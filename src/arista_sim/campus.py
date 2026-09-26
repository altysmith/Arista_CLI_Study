"""A bounded, loop-free Layer 2 campus lab. No routing or STP emulation."""
from collections import deque
from ipaddress import ip_interface

from .cli.session import Session

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
