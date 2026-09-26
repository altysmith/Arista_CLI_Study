"""A bounded, loop-free Layer 2 campus lab. No routing or STP emulation."""
from collections import deque
from ipaddress import ip_address, ip_interface, ip_network

from .cli.session import Session
from .models.device import StaticRoute

SWITCHES = ("DIST-1", "ACCESS-A", "ACCESS-B")
LINKS = [("DIST-1", "Ethernet1", "ACCESS-A", "Ethernet48"),
         ("DIST-1", "Ethernet2", "ACCESS-B", "Ethernet48")]
HOSTS = {
    "STAFF-A": ("ACCESS-A", "Ethernet1", "10.10.10.11/24", "02:00:00:00:10:11"),
    "STAFF-B": ("ACCESS-B", "Ethernet1", "10.10.10.12/24", "02:00:00:00:10:12"),
    "STUDENT-A": ("ACCESS-A", "Ethernet2", "10.20.20.11/24", "02:00:00:00:20:11"),
    "STUDENT-B": ("ACCESS-B", "Ethernet2", "10.20.20.12/24", "02:00:00:00:20:12"),
}


class CampusSession(Session):
    def __init__(self, campus, name):
        self.campus, self.node = campus, name
        super().__init__()

    def _show_lldp(self, _):
        lines = ["Port        Neighbor Device ID     Neighbor Port ID"]
        for a, ap, b, bp in LINKS:
            if self.node == b:
                a, ap, b, bp = b, bp, a, ap
            if self.node == a and self.campus.link_up(a, ap, b, bp):
                lines.append(f"{ap:<12}{self.campus.sessions[b].device.hostname:<23}{bp}")
        return "\n".join(lines) if len(lines) > 1 else lines[0] + "\nNo active neighbors"

    def _show_interfaces_status(self, args):
        lines = ["Port         Name                  Status         Vlan"]
        for name, port in self.device.interfaces.items():
            if args.get("interface") and name != args["interface"]:
                continue
            up = any((a == self.node and ap == name or b == self.node and bp == name)
                     and self.campus.link_up(a, ap, b, bp) for a, ap, b, bp in LINKS)
            up |= any(a == self.node and ap == name for a, ap, _, _ in HOSTS.values())
            status = "disabled" if not port.admin_up else "connected" if up else "notconnect"
            vlan = "trunk" if port.switchport_mode == "trunk" else str(port.access_vlan)
            lines.append(f"{name:<13}{port.description[:20]:<22}{status:<15}{vlan}")
        return "\n".join(lines)

    def _show_mac(self, _):
        rows = self.campus.mac[self.node]
        return "Vlan    Mac Address          Type       Ports\n" + ("\n".join(
            f"{v:<8}{m:<21}dynamic    {p}" for (v, m), p in sorted(rows.items())) or "No learned MAC addresses; generate host traffic first.")

    def _show_arp(self, _):
        return "No switch ARP entries: this lab has no participating Layer 3 switch interfaces. Host ARP tables are in the topology panel."


class Campus:
    def __init__(self, fault=""):
        self.fault = fault
        self.sessions = {name: CampusSession(self, name) for name in SWITCHES}
        self.mac = {name: {} for name in SWITCHES}
        self.arp = {name: {} for name in HOSTS}
        self.evidence = set()
        for name, cli in self.sessions.items():
            commands = ["enable", "configure terminal", f"hostname {name}"]
            for vlan, label in ((10, "STAFF"), (20, "STUDENTS"), (99, "MANAGEMENT")):
                commands += [f"vlan {vlan}", f"name {label}", "exit"]
            ports = ["Ethernet1", "Ethernet2"] if name == "DIST-1" else ["Ethernet48"]
            for port in ports:
                commands += [f"interface {port}", "switchport mode trunk", "switchport trunk allowed vlan 10,20,99", "exit"]
            if name != "DIST-1":
                for port, vlan in (("Ethernet1", 10), ("Ethernet2", 20)):
                    commands += [f"interface {port}", f"switchport access vlan {vlan}", "exit"]
            commands += ["end", "copy running-config startup-config", "disable"]
            for command in commands:
                result = cli.execute(command)
                if result.startswith("%"):
                    raise ValueError(result)
            cli.history.clear()
        if fault == "trunk":
            self.sessions["ACCESS-B"].device.interfaces["Ethernet48"].allowed_vlans = {10, 99}
        if fault == "access":
            self.sessions["ACCESS-A"].device.interfaces["Ethernet1"].access_vlan = 20

    def port(self, node, port):
        return self.sessions[node].device.interfaces[port]

    def link_up(self, a, ap, b, bp):
        return self.port(a, ap).admin_up and self.port(b, bp).admin_up

    def carries(self, node, port, vlan):
        p = self.port(node, port)
        v = self.sessions[node].device.vlans.get(vlan)
        return bool(v and v.active and p.admin_up and not p.channel_group and
                    ((p.switchport_mode == "access" and p.access_vlan == vlan) or
                     (p.switchport_mode == "trunk" and (p.allowed_vlans is None or vlan in p.allowed_vlans))))

    def transfer(self, a, ap, b, bp, vlan):
        if not self.carries(a, ap, vlan):
            return None
        out, inp = self.port(a, ap), self.port(b, bp)
        tag = vlan if out.switchport_mode == "trunk" and vlan != out.native_vlan else None
        if tag is not None and inp.switchport_mode != "trunk":
            return None
        received = tag if tag is not None else inp.native_vlan if inp.switchport_mode == "trunk" else inp.access_vlan
        return received if self.carries(b, bp, received) else None

    def flood(self, source, learn=False):
        node, port, _, mac = HOSTS[source]
        p = self.port(node, port)
        vlan = p.access_vlan
        if p.switchport_mode != "access" or not self.carries(node, port, vlan):
            return {}
        queue = deque([(node, port, vlan, [source, node])])
        visited, reached = set(), {}
        while queue:
            node, incoming, vlan, path = queue.popleft()
            if (node, vlan) in visited:
                continue
            visited.add((node, vlan))
            if learn:
                self.mac[node][(vlan, mac)] = incoming
            for host, (hn, hp, _, _) in HOSTS.items():
                if hn == node and hp != incoming and self.port(hn, hp).switchport_mode == "access" and self.carries(hn, hp, vlan):
                    reached[host] = path + [host]
            for a, ap, b, bp in LINKS:
                if node == b:
                    a, ap, b, bp = b, bp, a, ap
                if node == a and ap != incoming:
                    received = self.transfer(a, ap, b, bp, vlan)
                    if received is not None:
                        queue.append((b, bp, received, path + [b]))
        return reached

    def ping(self, source, destination, learn=True):
        if source not in HOSTS or destination not in HOSTS or source == destination:
            raise ValueError("Choose two different lab hosts")
        if learn:
            self.evidence.add("host_ping")
        src, dst = HOSTS[source], HOSTS[destination]
        if ip_interface(src[2]).network != ip_interface(dst[2]).network:
            return {"success": False, "output": "No gateway configured. This lab supports same-subnet Layer 2 traffic only."}
        forward = self.flood(source, learn)
        # The destination replies only if it received the request.
        reverse = self.flood(destination, learn) if destination in forward else {}
        success = destination in forward and source in reverse
        if success and learn:
            self.arp[source][str(ip_interface(dst[2]).ip)] = dst[3]
            self.arp[destination][str(ip_interface(src[2]).ip)] = src[3]
        return {"success": success, "output": f"{source} → {destination}: " +
                ("reply received (simulated ICMP). Path: " + " → ".join(forward[destination]) if success else "request timed out; inspect access VLANs, trunks, and interface state.")}

    def grade(self):
        results = []
        for source, destination in (("STAFF-A", "STAFF-B"), ("STUDENT-A", "STUDENT-B")):
            results.append({"label": f"{source} can reach {destination}", "passed": self.ping(source, destination, False)["success"]})
        isolated = all(not any(h.startswith("STUDENT") for h in self.flood(s)) for s in ("STAFF-A", "STAFF-B"))
        results.append({"label": "Staff and student Layer 2 networks remain isolated", "passed": isolated})
        results.append({"label": "VLAN 99 remains allowed on every uplink", "passed": all(
            self.transfer(a, ap, b, bp, 99) == 99 and self.transfer(b, bp, a, ap, 99) == 99 for a, ap, b, bp in LINKS)})
        histories = [command.casefold() for cli in self.sessions.values() for command in cli.history]
        process = [
            {"label": "Tested host connectivity", "passed": "host_ping" in self.evidence},
            {"label": "Mapped an uplink with LLDP", "passed": any(command.startswith("show lldp") for command in histories)},
        ]
        if self.fault == "access":
            process.append({"label": "Inspected interface status", "passed": any(command.startswith("show interfaces status") for command in histories)})
        else:
            process.append({"label": "Inspected trunk state", "passed": any(command.startswith("show interfaces trunk") for command in histories)})
        return {"results": results, "passed": all(r["passed"] for r in results), "passed_count": sum(r["passed"] for r in results), "total_count": len(results), "process": process, "process_passed_count": sum(r["passed"] for r in process), "process_total_count": len(process)}

    def view(self):
        return {"switches": list(SWITCHES), "links": [{"a": a, "ap": ap, "b": b, "bp": bp,
                "up": self.link_up(a, ap, b, bp)} for a, ap, b, bp in LINKS],
                "hosts": [{"id": h, "switch": n, "port": p, "address": ip, "mac": mac, "arp": self.arp[h]} for h, (n, p, ip, mac) in HOSTS.items()]}


ROUTED_SWITCHES = ("EDGE-A", "CORE-1", "EDGE-B")
ROUTED_LINKS = [("EDGE-A", "Ethernet1", "CORE-1", "Ethernet1"),
                ("CORE-1", "Ethernet2", "EDGE-B", "Ethernet1")]
ROUTED_HOSTS = {
    "SITE-A": ("EDGE-A", "Ethernet2", "10.10.10.10/24", "10.10.10.1", "02:00:00:01:10:10"),
    "SITE-B": ("EDGE-B", "Ethernet2", "10.20.20.10/24", "10.20.20.1", "02:00:00:01:20:10"),
}


class RoutedCampusSession(Session):
    def __init__(self, campus, name):
        self.campus, self.node = campus, name
        super().__init__()

    def _show_lldp(self, _):
        lines = ["Port        Neighbor Device ID     Neighbor Port ID"]
        for a, ap, b, bp in ROUTED_LINKS:
            if self.node == b:
                a, ap, b, bp = b, bp, a, ap
            if self.node == a and self.campus.link_up(a, ap, b, bp):
                lines.append(f"{ap:<12}{b:<23}{bp}")
        return "\n".join(lines) if len(lines) > 1 else lines[0] + "\nNo active neighbors"

    def _show_interfaces_status(self, args):
        lines = ["Port         Name                  Status         Vlan"]
        for name, port in self.device.interfaces.items():
            if args.get("interface") and name != args["interface"]:
                continue
            linked = any((a == self.node and ap == name or b == self.node and bp == name)
                         and self.campus.link_up(a, ap, b, bp) for a, ap, b, bp in ROUTED_LINKS)
            linked |= any(a == self.node and ap == name for a, ap, *_ in ROUTED_HOSTS.values())
            status = "disabled" if not port.admin_up else "connected" if linked else "notconnect"
            vlan = "routed" if port.switchport_mode == "routed" else str(port.access_vlan)
            lines.append(f"{name:<13}{port.description[:20]:<22}{status:<15}{vlan}")
        return "\n".join(lines)

    def _show_ospf_neighbors(self, _):
        return self.campus.ospf_neighbor_output(self.node)

    def _show_ospf_interfaces(self, _):
        return self.campus.ospf_interface_output(self.node)

    def _show_ip_route(self, _):
        return self.campus.ip_route_output(self.node)


class RoutedCampus:
    """A fixed three-router topology that evaluates static IPv4 forwarding and return paths only."""
    def __init__(self, fault="static"):
        if fault not in ("static", "next-hop", "ospf-area", "ospf-route", "ospf-link", "ospf-specificity", "ospf-source"):
            raise ValueError("Unknown routed campus fault")
        self.fault = fault
        self.sessions = {name: RoutedCampusSession(self, name) for name in ROUTED_SWITCHES}
        self.arp = {name: {} for name in ROUTED_HOSTS}
        self.mac = {name: {} for name in ROUTED_SWITCHES}
        self.evidence = set()
        self._configure()

    def _run(self, node, commands):
        cli = self.sessions[node]
        for command in commands:
            result = cli.execute(command)
            if result.startswith("%"):
                raise ValueError(result)
        cli.history.clear()

    def _configure(self):
        interfaces = {
            "EDGE-A": (("Ethernet1", "192.0.2.1/30"), ("Ethernet2", "10.10.10.1/24")),
            "CORE-1": (("Ethernet1", "192.0.2.2/30"), ("Ethernet2", "198.51.100.1/30")),
            "EDGE-B": (("Ethernet1", "198.51.100.2/30"), ("Ethernet2", "10.20.20.1/24")),
        }
        routes = {
            "EDGE-A": (("10.20.20.0/24", "192.0.2.6" if self.fault == "next-hop" else "192.0.2.2"),),
            "CORE-1": (("10.10.10.0/24", "192.0.2.1"), ("10.20.20.0/24", "198.51.100.2")),
            "EDGE-B": (("10.10.10.0/24", "198.51.100.1"),) if self.fault == "next-hop" else (),
        }
        if self.fault in ("ospf-area", "ospf-route", "ospf-link", "ospf-specificity", "ospf-source"):
            routes = {node: () for node in ROUTED_SWITCHES}
        if self.fault == "ospf-specificity":
            routes["EDGE-A"] = (("10.20.0.0/16", "192.0.2.6"),)
        if self.fault == "ospf-source":
            routes["EDGE-A"] = (("10.20.20.0/24", "192.0.2.6"),)
        for node in ROUTED_SWITCHES:
            commands = ["enable", "configure terminal", f"hostname {node}", "ip routing"]
            for port, address in interfaces[node]:
                commands += [f"interface {port}", "no switchport", f"ip address {address}", "no shutdown", "exit"]
            for prefix, next_hop in routes[node]:
                commands.append(f"ip route {prefix} {next_hop}")
            if self.fault in ("ospf-area", "ospf-route", "ospf-link", "ospf-specificity", "ospf-source"):
                router_id = {"EDGE-A": "1.1.1.1", "CORE-1": "2.2.2.2", "EDGE-B": "3.3.3.3"}[node]
                network = {"EDGE-A": "192.0.2.0/30", "CORE-1": "192.0.2.0/30", "EDGE-B": "198.51.100.0/30"}[node]
                area = "1" if self.fault == "ospf-area" and node == "EDGE-B" else "0"
                if node == "CORE-1":
                    commands += ["router ospf 1", f"router-id {router_id}", "network 192.0.2.0/30 area 0", "network 198.51.100.0/30 area 0", "exit"]
                else:
                    commands += ["router ospf 1", f"router-id {router_id}", f"network {network} area {area}"]
                    if self.fault in ("ospf-route", "ospf-link", "ospf-specificity", "ospf-source") and node == "EDGE-A":
                        commands.append("network 10.10.10.0/24 area 0")
                    if self.fault in ("ospf-link", "ospf-specificity", "ospf-source") and node == "EDGE-B":
                        commands.append("network 10.20.20.0/24 area 0")
                    if self.fault == "ospf-route" and node == "EDGE-B":
                        # The missing SITE-B LAN advertisement is the ticket fault.
                        pass
                    commands.append("exit")
            commands += ["end", "copy running-config startup-config", "disable"]
            self._run(node, commands)
        if self.fault == "ospf-link":
            self.sessions["EDGE-B"].device.interfaces["Ethernet1"].admin_up = False

    def _ospf_assignment(self, node, port):
        for process in self.sessions[node].device.ospf_processes.values():
            for network, area in process.networks:
                if any(ip_interface(address).ip in ip_network(network, strict=False) for address in self.port(node, port).ipv4_addresses):
                    return process, area
        return None, None

    def ospf_neighbor_state(self, node, port):
        peer = self._linked_peer(node, port)
        if not peer:
            return None, "link down"
        remote, remote_port = peer
        local_process, local_area = self._ospf_assignment(node, port)
        remote_process, remote_area = self._ospf_assignment(remote, remote_port)
        if not local_process or not remote_process:
            return remote, "OSPF not enabled"
        if local_area != remote_area:
            return remote, "area mismatch"
        return remote, "Full"

    def ospf_neighbor_output(self, node):
        if not self.sessions[node].device.ospf_processes:
            return "OSPF is not configured"
        lines = ["Neighbor ID     Pri   State      Address         Interface"]
        issues = []
        for a, ap, b, bp in ROUTED_LINKS:
            if node not in (a, b):
                continue
            port = ap if node == a else bp
            remote, state = self.ospf_neighbor_state(node, port)
            if state == "Full":
                process = next(iter(self.sessions[remote].device.ospf_processes.values()))
                address = self.port(remote, bp if remote == b else ap).ipv4_addresses[0].split("/")[0]
                lines.append(f"{process.router_id:<16}1     FULL/-     {address:<16}{port}")
            else:
                issues.append(f"{port}: {state}")
        return "\n".join(lines if len(lines) > 1 else lines + ["No OSPF neighbors; " + "; ".join(issues)])

    def ospf_interface_output(self, node):
        lines = ["Interface        PID   Area        IP Address          State Nbrs"]
        for a, ap, b, bp in ROUTED_LINKS:
            if node not in (a, b):
                continue
            port = ap if node == a else bp
            process, area = self._ospf_assignment(node, port)
            if process:
                _, state = self.ospf_neighbor_state(node, port)
                interface_state = "Up" if self.port(node, port).admin_up else "Down"
                lines.append(f"{port:<16}{process.process_id:<6}{area:<12}{self.port(node, port).ipv4_addresses[0]:<20}{interface_state:<6}{1 if state == 'Full' else 0}")
        return "\n".join(lines) if len(lines) > 1 else "OSPF is not configured on routed interfaces"

    def _ospf_component(self, node):
        reached, queue = {node}, [node]
        while queue:
            current = queue.pop(0)
            for a, ap, b, bp in ROUTED_LINKS:
                if current not in (a, b):
                    continue
                port = ap if current == a else bp
                peer, state = self.ospf_neighbor_state(current, port)
                if state == "Full" and peer not in reached:
                    reached.add(peer); queue.append(peer)
        return reached

    def ospf_routes(self, node):
        component = self._ospf_component(node)
        direct = {str(ip_interface(address).network) for port in self.sessions[node].device.interfaces.values() for address in port.ipv4_addresses}
        routes = []
        for remote in component - {node}:
            for process in self.sessions[remote].device.ospf_processes.values():
                for network, _ in process.networks:
                    if network not in direct and network not in {route["prefix"] for route in routes}:
                        routes.append({"prefix": network, "owner": remote})
        return routes

    def _ospf_next_hop(self, node, owner):
        queue, previous = [node], {node: None}
        while queue:
            current = queue.pop(0)
            if current == owner:
                break
            for a, ap, b, bp in ROUTED_LINKS:
                if current not in (a, b):
                    continue
                port = ap if current == a else bp
                peer, state = self.ospf_neighbor_state(current, port)
                if state == "Full" and peer not in previous:
                    previous[peer] = (current, port)
                    queue.append(peer)
        if owner not in previous:
            return None
        step = owner
        while previous[step] and previous[step][0] != node:
            step = previous[step][0]
        _, port = previous[step]
        peer_port = next(bp if a == node and ap == port else ap for a, ap, b, bp in ROUTED_LINKS if (a == node and ap == port) or (b == node and bp == port))
        return self.port(node, port), self.port(step, peer_port).ipv4_addresses[0].split("/")[0]

    def ip_route_output(self, node):
        lines = ["Codes: C - connected, S - static, O - OSPF", ""]
        device = self.sessions[node].device
        for port in device.interfaces.values():
            for address in port.ipv4_addresses:
                lines.append(f" C        {ip_interface(address).network} is directly connected, {port.name}")
        lines.extend(f" S        {route.prefix} via {route.next_hop}" for route in device.static_routes)
        lines.extend(f" O        {route['prefix']} via OSPF path to {route['owner']}" for route in self.ospf_routes(node))
        return "\n".join(lines)

    def route_decision(self, node, destination):
        address = ip_address(destination)
        device = self.sessions[node].device
        static = [(ip_network(route.prefix, strict=False).prefixlen, 1, "static", route.prefix, route.next_hop) for route in device.static_routes if address in ip_network(route.prefix, strict=False)]
        ospf = [(ip_network(route["prefix"], strict=False).prefixlen, 0, "OSPF", route["prefix"], route["owner"]) for route in self.ospf_routes(node) if address in ip_network(route["prefix"], strict=False)]
        candidates = static + ospf
        if not candidates:
            return None
        prefix, priority, source, network, via = max(candidates, key=lambda item: (item[0], item[1]))
        same_prefix = [item for item in candidates if item[0] == prefix]
        reason = "source preference after an equal-prefix tie" if len(same_prefix) > 1 else "longest matching prefix"
        return {"destination": destination, "prefix": network, "source": source, "via": via, "reason": reason}

    def port(self, node, port):
        return self.sessions[node].device.interfaces[port]

    def link_up(self, a, ap, b, bp):
        return self.port(a, ap).admin_up and self.port(b, bp).admin_up

    @staticmethod
    def _has_address(port, address):
        return any(ip_address(address) == ip_interface(configured).ip for configured in port.ipv4_addresses)

    def _linked_peer(self, node, port):
        for a, ap, b, bp in ROUTED_LINKS:
            if node == a and port == ap and self.link_up(a, ap, b, bp):
                return b, bp
            if node == b and port == bp and self.link_up(a, ap, b, bp):
                return a, ap
        return None

    def _route(self, node, destination):
        device = self.sessions[node].device
        if not device.ip_routing:
            return None, "IP routing is disabled"
        address = ip_address(destination)
        direct = [(ip_interface(configured).network.prefixlen, port) for port in device.interfaces.values()
                  for configured in port.ipv4_addresses if address in ip_interface(configured).network]
        if direct:
            return max(direct, key=lambda item: item[0])[1], None
        matches = [(ip_network(route.prefix, strict=False).prefixlen, 1, route) for route in device.static_routes if address in ip_network(route.prefix, strict=False)]
        matches += [(ip_network(route["prefix"], strict=False).prefixlen, 0, route) for route in self.ospf_routes(node) if address in ip_network(route["prefix"], strict=False)]
        if not matches:
            return None, "no matching static or OSPF route"
        _, source_priority, route = max(matches, key=lambda item: (item[0], item[1]))
        if source_priority == 0:
            return self._ospf_next_hop(node, route["owner"])
        for port in device.interfaces.values():
            if any(ip_address(route.next_hop) in ip_interface(configured).network for configured in port.ipv4_addresses):
                return port, route.next_hop
        return None, "next hop is not directly reachable"

    def _forward(self, source, destination):
        host = ROUTED_HOSTS[source]
        destination_address = str(ip_interface(ROUTED_HOSTS[destination][2]).ip)
        gateway_port = self.port(host[0], host[1])
        if not gateway_port.admin_up or not self._has_address(gateway_port, host[3]):
            return False, [source], "host gateway is unavailable"
        node, path = host[0], [source, host[0]]
        for _ in range(len(ROUTED_SWITCHES) + 1):
            port, detail = self._route(node, destination_address)
            if port is None:
                return False, path, f"{node}: {detail}"
            peer = self._linked_peer(node, port.name)
            if peer is None:
                if any(n == node and p == port.name and str(ip_interface(address).ip) == destination_address
                       for n, p, address, *_ in ROUTED_HOSTS.values()):
                    return True, path + [destination], ""
                return False, path, f"{node}: destination is not reachable on {port.name}"
            next_node, next_port = peer
            if not port.admin_up or not self.port(next_node, next_port).admin_up:
                return False, path, f"{node}: routed link is down"
            if detail and not self._has_address(self.port(next_node, next_port), detail):
                return False, path, f"{node}: next hop {detail} is unavailable"
            node = next_node
            path.append(node)
        return False, path, "routing loop detected"

    def ping(self, source, destination, learn=True):
        if source not in ROUTED_HOSTS or destination not in ROUTED_HOSTS or source == destination:
            raise ValueError("Choose two different routed-lab hosts")
        if learn:
            self.evidence.add("host_ping")
        forward, forward_path, reason = self._forward(source, destination)
        reverse, reverse_path, reverse_reason = self._forward(destination, source) if forward else (False, [], "")
        if forward and reverse:
            self.arp[source][str(ip_interface(ROUTED_HOSTS[destination][2]).ip)] = ROUTED_HOSTS[destination][4]
            self.arp[destination][str(ip_interface(ROUTED_HOSTS[source][2]).ip)] = ROUTED_HOSTS[source][4]
            destination_ip = str(ip_interface(ROUTED_HOSTS[destination][2]).ip)
            source_ip = str(ip_interface(ROUTED_HOSTS[source][2]).ip)
            timeline = [{"direction": f"{source} → {destination}", "routes": [decision for node in forward_path if node in self.sessions and (decision := self.route_decision(node, destination_ip))]}, {"direction": f"{destination} → {source}", "routes": [decision for node in reverse_path if node in self.sessions and (decision := self.route_decision(node, source_ip))]}]
            return {"success": True, "output": f"{source} → {destination}: reply received (simulated IPv4). Path: " + " → ".join(forward_path), "timeline": timeline}
        detail = reason if not forward else f"return path failed: {reverse_reason}"
        failed_path = forward_path if not forward else reverse_path
        failed_destination = str(ip_interface(ROUTED_HOSTS[destination if not forward else source][2]).ip)
        direction = f"{source} → {destination}" if not forward else f"{destination} → {source}"
        timeline = [{"direction": direction, "routes": [decision for node in failed_path if node in self.sessions and (decision := self.route_decision(node, failed_destination))], "failure": detail}]
        return {"success": False, "output": f"{source} → {destination}: request timed out; {detail}.", "timeline": timeline}

    def grade(self):
        if self.fault == "ospf-source":
            static_removed = not any(route.prefix == "10.20.20.0/24" for route in self.sessions["EDGE-A"].device.static_routes)
            success = self.ping("SITE-A", "SITE-B", False)["success"]
            histories = [command.casefold() for cli in self.sessions.values() for command in cli.history]
            results = [{"label": "The conflicting static /24 is removed", "passed": static_removed}, {"label": "SITE-A reaches SITE-B using the OSPF /24", "passed": success}]
            process = [{"label": "Inspected the IPv4 route table", "passed": any(command.startswith("show ip route") for command in histories)}]
            return {"results": results, "passed": all(item["passed"] for item in results), "passed_count": sum(item["passed"] for item in results), "total_count": len(results), "process": process, "process_passed_count": sum(item["passed"] for item in process), "process_total_count": len(process)}
        if self.fault == "ospf-link":
            full = all(self.ospf_neighbor_state(node, port)[1] == "Full" for node, port in ((a, ap) for a, ap, _, _ in ROUTED_LINKS))
            success = self.ping("SITE-A", "SITE-B", False)["success"]
            histories = [command.casefold() for cli in self.sessions.values() for command in cli.history]
            results = [{"label": "CORE-1 and EDGE-B form a Full OSPF adjacency", "passed": self.ospf_neighbor_state("EDGE-B", "Ethernet1")[1] == "Full"}, {"label": "SITE-A reaches SITE-B over the restored OSPF path", "passed": success}]
            process = [{"label": "Inspected OSPF interface state", "passed": any(command.startswith("show ip ospf interface brief") for command in histories)}, {"label": "Inspected OSPF neighbors", "passed": any(command.startswith("show ip ospf neighbor") for command in histories)}]
            return {"results": results, "passed": all(item["passed"] for item in results) and full, "passed_count": sum(item["passed"] for item in results), "total_count": len(results), "process": process, "process_passed_count": sum(item["passed"] for item in process), "process_total_count": len(process)}
        if self.fault == "ospf-route":
            advertised = any(network == "10.20.20.0/24" and area in ("0", "0.0.0.0") for process in self.sessions["EDGE-B"].device.ospf_processes.values() for network, area in process.networks)
            learned = any(route["prefix"] == "10.20.20.0/24" for route in self.ospf_routes("EDGE-A"))
            histories = [command.casefold() for cli in self.sessions.values() for command in cli.history]
            results = [{"label": "EDGE-B advertises the SITE-B LAN in area 0", "passed": advertised}, {"label": "EDGE-A selects an OSPF route to SITE-B", "passed": learned}]
            process = [{"label": "Inspected OSPF neighbors", "passed": any(command.startswith("show ip ospf neighbor") for command in histories)}, {"label": "Inspected the IPv4 route table", "passed": any(command.startswith("show ip route") for command in histories)}]
            return {"results": results, "passed": all(item["passed"] for item in results), "passed_count": sum(item["passed"] for item in results), "total_count": len(results), "process": process, "process_passed_count": sum(item["passed"] for item in process), "process_total_count": len(process)}
        if self.fault == "ospf-area":
            links = [(a, ap) for a, ap, _, _ in ROUTED_LINKS] + [(b, bp) for _, _, b, bp in ROUTED_LINKS]
            full = [(node, port, self.ospf_neighbor_state(node, port)[1] == "Full") for node, port in links]
            histories = [command.casefold() for cli in self.sessions.values() for command in cli.history]
            results = [{"label": f"{node} {port} has a Full OSPF neighbor", "passed": passed} for node, port, passed in full]
            process = [{"label": "Inspected OSPF neighbors", "passed": any(command.startswith("show ip ospf neighbor") for command in histories)}, {"label": "Inspected OSPF interfaces", "passed": any(command.startswith("show ip ospf interface brief") for command in histories)}]
            return {"results": results, "passed": all(item["passed"] for item in results), "passed_count": sum(item["passed"] for item in results), "total_count": len(results), "process": process, "process_passed_count": sum(item["passed"] for item in process), "process_total_count": len(process)}
        success = self.ping("SITE-A", "SITE-B", False)["success"]
        histories = [command.casefold() for cli in self.sessions.values() for command in cli.history]
        if self.fault == "next-hop":
            repair = any(route.prefix == "10.20.20.0/24" and route.next_hop == "192.0.2.2" for route in self.sessions["EDGE-A"].device.static_routes)
            repair_label = "EDGE-A uses the reachable CORE-1 next hop"
        else:
            repair = any(route.prefix == "10.10.10.0/24" and route.next_hop == "198.51.100.1" for route in self.sessions["EDGE-B"].device.static_routes)
            repair_label = "SITE-B has a return route to SITE-A"
        results = [{"label": "SITE-A reaches SITE-B through the routed path", "passed": success},
                   {"label": repair_label, "passed": repair}]
        process = [{"label": "Tested end-to-end host connectivity", "passed": "host_ping" in self.evidence},
                   {"label": "Inspected a routing table", "passed": any(command.startswith("show ip route") for command in histories)},
                   {"label": "Mapped a routed link with LLDP", "passed": any(command.startswith("show lldp") for command in histories)}]
        return {"results": results, "passed": all(item["passed"] for item in results), "passed_count": sum(item["passed"] for item in results), "total_count": len(results), "process": process, "process_passed_count": sum(item["passed"] for item in process), "process_total_count": len(process)}

    def view(self):
        devices = []
        for name in ROUTED_SWITCHES:
            device = self.sessions[name].device
            interfaces = [{"name": port.name, "addresses": list(port.ipv4_addresses), "up": port.admin_up}
                          for port in device.interfaces.values() if port.ipv4_addresses]
            routes = [{"prefix": route.prefix, "next_hop": route.next_hop} for route in device.static_routes]
            decisions = [decision for host, (_, _, address, *_ ) in ROUTED_HOSTS.items() if (decision := self.route_decision(name, str(ip_interface(address).ip)))]
            devices.append({"name": name, "interfaces": interfaces, "routes": routes, "decisions": decisions})
        return {"title": "Three-router static-routing path", "subtitle": "Fictional routed topology · static IPv4 only", "limits": "The simulator evaluates directly connected and static IPv4 routes plus return paths. It does not model OSPF adjacency or route exchange, ARP on routers, ACL enforcement, packet loss, or timing.", "switches": list(ROUTED_SWITCHES), "links": [{"a": a, "ap": ap, "b": b, "bp": bp, "up": self.link_up(a, ap, b, bp)} for a, ap, b, bp in ROUTED_LINKS], "hosts": [{"id": name, "switch": node, "port": port, "address": address, "mac": mac, "arp": self.arp[name]} for name, (node, port, address, gateway, mac) in ROUTED_HOSTS.items()], "devices": devices}
