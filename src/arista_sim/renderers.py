from __future__ import annotations

from ipaddress import ip_interface

from .models.device import AccessList, DeviceState, Interface


def short_interface(name: str) -> str:
    replacements = (("Ethernet", "Et"), ("Management", "Ma"), ("Port-Channel", "Po"), ("Loopback", "Lo"))
    for long, short in replacements:
        if name.startswith(long):
            return name.replace(long, short, 1)
    return name


def _vlan_list(vlans: set[int]) -> str:
    if not vlans:
        return "none"
    values = sorted(vlans)
    ranges: list[str] = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = value
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(ranges)


def running_config(device: DeviceState) -> str:
    lines = ["!", f"hostname {device.hostname}", "!"]
    if device.ip_routing:
        lines.extend(["ip routing", "!"])
    if device.ipv6_unicast_routing:
        lines.extend(["ipv6 unicast-routing", "!"])
    if device.spanning_tree_mode != "mstp":
        lines.extend([f"spanning-tree mode {device.spanning_tree_mode}", "!"])
    for vlan, priority in sorted(device.spanning_tree_priorities.items()):
        lines.append(f"spanning-tree vlan {vlan} priority {priority}")
    if device.spanning_tree_priorities:
        lines.append("!")
    for vlan_id, vlan in sorted(device.vlans.items()):
        if vlan_id == 1 and vlan.name == "default":
            continue
        lines.append(f"vlan {vlan_id}")
        if vlan.name:
            lines.append(f"   name {vlan.name}")
        lines.append("!")
    for interface in device.interfaces.values():
        if _interface_is_default(interface):
            continue
        lines.append(f"interface {interface.name}")
        if interface.description:
            lines.append(f"   description {interface.description}")
        if interface.switchport_mode == "routed":
            if interface.is_switchport_capable:
                lines.append("   no switchport")
        else:
            lines.append(f"   switchport mode {interface.switchport_mode}")
            if interface.switchport_mode == "access":
                lines.append(f"   switchport access vlan {interface.access_vlan}")
            elif interface.allowed_vlans is not None:
                lines.append(f"   switchport trunk allowed vlan {_vlan_list(interface.allowed_vlans)}")
            if interface.switchport_mode == "trunk" and interface.native_vlan != 1:
                lines.append(f"   switchport trunk native vlan {interface.native_vlan}")
        if interface.encapsulation_vlan is not None:
            lines.append(f"   encapsulation dot1q vlan {interface.encapsulation_vlan}")
        lines.extend(f"   ip address {address}" for address in interface.ipv4_addresses)
        lines.extend(f"   ipv6 address {address}" for address in interface.ipv6_addresses)
        if interface.channel_group is not None:
            lines.append(f"   channel-group {interface.channel_group} mode {interface.channel_mode}")
        if interface.mlag_id is not None:
            lines.append(f"   mlag {interface.mlag_id}")
        if interface.stp_portfast != "auto":
            suffix = "" if interface.stp_portfast == "enabled" else f" {interface.stp_portfast}"
            lines.append(f"   spanning-tree portfast{suffix}")
        if interface.stp_port_priority != 128:
            lines.append(f"   spanning-tree port-priority {interface.stp_port_priority}")
        for direction, acl in interface.ip_access_groups.items():
            lines.append(f"   ip access-group {acl} {direction}")
        for direction, policy in interface.service_policies.items():
            lines.append(f"   service-policy type qos {direction} {policy}")
        if not interface.autostate:
            lines.append("   no autostate")
        if not interface.admin_up:
            lines.append("   shutdown")
        lines.append("!")
    for route in device.static_routes:
        lines.append(f"ip route {route.prefix} {route.next_hop}")
    for route in device.ipv6_static_routes:
        lines.append(f"ipv6 route {route.prefix} {route.next_hop}")
    if device.static_routes or device.ipv6_static_routes:
        lines.append("!")
    if device.rip_networks:
        lines.append("router rip")
        lines.extend(f"   network {network}" for network in device.rip_networks)
        lines.extend(f"   redistribute {source}" for source in sorted(device.rip_redistribute))
        lines.append("!")
    for process in device.ospf_processes.values():
        lines.append(f"router ospf {process.process_id}")
        if process.router_id:
            lines.append(f"   router-id {process.router_id}")
        lines.extend(f"   network {network} area {area}" for network, area in process.networks)
        lines.extend(f"   redistribute {source}" for source in sorted(process.redistribute))
        lines.append("!")
    for acl in device.access_lists.values():
        lines.append(f"ip access-list {acl.name}")
        lines.extend(f"   {entry}" for entry in acl.entries)
        lines.append("!")
    if device.control_plane_acl != "default-control-plane-acl":
        lines.extend(["control-plane", f"   ip access-group {device.control_plane_acl} in", "!"])
    if device.ssh_service_acl:
        lines.extend(["management ssh", f"   ip access-group {device.ssh_service_acl} in", "!"])
    if any((device.mlag.domain_id, device.mlag.local_interface, device.mlag.peer_address, device.mlag.peer_link)):
        lines.append("mlag configuration")
        for command in (
            f"domain-id {device.mlag.domain_id}" if device.mlag.domain_id else "",
            f"local-interface {device.mlag.local_interface}" if device.mlag.local_interface else "",
            f"peer-address {device.mlag.peer_address}" if device.mlag.peer_address else "",
            f"peer-link {device.mlag.peer_link}" if device.mlag.peer_link else "",
            "shutdown" if device.mlag.shutdown else "",
        ):
            if command:
                lines.append(f"   {command}")
        lines.append("!")
    for class_map in device.class_maps.values():
        lines.append(f"class-map type qos match-any {class_map.name}")
        if class_map.access_group:
            lines.append(f"   match ip access-group {class_map.access_group}")
        lines.append("!")
    for policy in device.policy_maps.values():
        lines.append(f"policy-map type quality-of-service {policy.name}")
        for policy_class in policy.classes.values():
            lines.append(f"   class {policy_class.name}")
            lines.extend(f"      {action}" for action in policy_class.actions)
        lines.append("!")
    lines.append("end")
    return "\n".join(lines)


def _interface_is_default(interface: Interface) -> bool:
    physical_default = interface.name.startswith("Ethernet") and "." not in interface.name
    management_default = interface.name == "Management1"
    return (
        (physical_default or management_default)
        and not interface.description
        and interface.admin_up
        and interface.switchport_mode == ("routed" if management_default else "access")
        and interface.access_vlan == 1
        and interface.native_vlan == 1
        and interface.allowed_vlans is None
        and not interface.ipv4_addresses
        and not interface.ipv6_addresses
        and interface.channel_group is None
        and interface.mlag_id is None
        and interface.stp_portfast == "auto"
        and interface.stp_port_priority == 128
        and not interface.ip_access_groups
        and not interface.service_policies
    )


def show_vlan(device: DeviceState, vlan_id: int | None = None) -> str:
    lines = ["VLAN  Name                             Status    Ports", "----- -------------------------------- --------- -------------------------------"]
    vlans = device.vlans.items() if vlan_id is None else [(vlan_id, device.vlans[vlan_id])]
    for current_id, vlan in sorted(vlans):
        ports = [short_interface(i.name) for i in device.interfaces.values() if i.switchport_mode == "access" and i.access_vlan == current_id]
        lines.append(f"{current_id:<5} {vlan.name or f'VLAN{current_id:04d}':<32} {'active':<9} {', '.join(ports)}".rstrip())
    return "\n".join(lines)


def show_switchport(interface: Interface) -> str:
    if not interface.is_switchport_capable:
        return f"Name: {short_interface(interface.name)}\nSwitchport: Disabled"
    operational = "static access" if interface.switchport_mode == "access" else interface.switchport_mode
    return "\n".join([f"Name: {short_interface(interface.name)}", f"Switchport: {'Disabled' if interface.switchport_mode == 'routed' else 'Enabled'}", f"Administrative Mode: {interface.switchport_mode}", f"Operational Mode: {operational}", f"Access Mode VLAN: {interface.access_vlan}", f"Trunking Native Mode VLAN: {interface.native_vlan}", "Trunking VLANs Enabled: " + ("ALL" if interface.allowed_vlans is None else _vlan_list(interface.allowed_vlans))])


def show_interfaces_trunk(device: DeviceState, interface_name: str | None = None) -> str:
    interfaces = [i for i in device.interfaces.values() if i.switchport_mode == "trunk" and (interface_name is None or i.name == interface_name)]
    if not interfaces:
        return "No trunk interfaces configured"
    lines = ["Port            Mode            Status          Native vlan"]
    for interface in interfaces:
        lines.append(f"{short_interface(interface.name):<15} {'trunk':<15} {('trunking' if interface.admin_up else 'notconnect'):<15} {interface.native_vlan}")
    lines.extend(["", "Port            Vlans allowed"])
    for interface in interfaces:
        lines.append(f"{short_interface(interface.name):<15} {'ALL' if interface.allowed_vlans is None else _vlan_list(interface.allowed_vlans)}")
    lines.extend(["", "Port            Vlans allowed and active in management domain"])
    active = set(device.vlans)
    for interface in interfaces:
        permitted = active if interface.allowed_vlans is None else active & interface.allowed_vlans
        lines.append(f"{short_interface(interface.name):<15} {_vlan_list(permitted)}")
    return "\n".join(lines)


def show_interfaces_status(device: DeviceState, interface_name: str | None = None) -> str:
    interfaces = [i for i in device.interfaces.values() if interface_name is None or i.name == interface_name]
    lines = ["Port      Name               Status       Vlan  Duplex Speed Type"]
    for interface in interfaces:
        status = "connected" if interface.admin_up else "disabled"
        vlan = "routed" if interface.switchport_mode == "routed" else ("trunk" if interface.switchport_mode == "trunk" else str(interface.access_vlan))
        lines.append(f"{short_interface(interface.name):<9} {interface.description[:18]:<18} {status:<12} {vlan:<7} {'full':<6} {'auto':<5} simulated")
    return "\n".join(lines)


def show_interfaces_vlans(device: DeviceState, interface_name: str | None = None) -> str:
    interfaces = [i for i in device.interfaces.values() if interface_name is None or i.name == interface_name]
    lines = ["Port       Untagged Tagged"]
    for interface in interfaces:
        if interface.switchport_mode == "routed":
            untagged, tagged = "-", "-"
        elif interface.switchport_mode == "access":
            untagged, tagged = str(interface.access_vlan), "-"
        else:
            untagged = str(interface.native_vlan)
            tagged = "ALL" if interface.allowed_vlans is None else _vlan_list(interface.allowed_vlans - {interface.native_vlan})
        lines.append(f"{short_interface(interface.name):<10} {untagged:<8} {tagged}")
    return "\n".join(lines)


def show_ip_interface_brief(device: DeviceState, ipv6: bool = False) -> str:
    lines = ["Interface              IP Address                         Status     Protocol"]
    for interface in device.interfaces.values():
        addresses = interface.ipv6_addresses if ipv6 else interface.ipv4_addresses
        if addresses or interface.name.startswith(("Management", "Vlan", "Loopback")) or interface.switchport_mode == "routed":
            address = addresses[0] if addresses else "unassigned"
            status = "up" if interface.admin_up else "down"
            lines.append(f"{short_interface(interface.name):<22} {address:<34} {status:<10} {status}")
    return "\n".join(lines)


def show_ip_route(device: DeviceState, ipv6: bool = False) -> str:
    lines = ["Codes: C - connected, S - static, R - RIP", ""]
    for interface in device.interfaces.values():
        addresses = interface.ipv6_addresses if ipv6 else interface.ipv4_addresses
        for address in addresses:
            network = ip_interface(address).network
            lines.append(f" C        {network} is directly connected, {short_interface(interface.name)}")
    routes = device.ipv6_static_routes if ipv6 else device.static_routes
    lines.extend(f" S        {route.prefix} via {route.next_hop}" for route in routes)
    if not any(line.startswith((" C", " S")) for line in lines):
        lines.append("Gateway of last resort is not set" if not ipv6 else "No IPv6 routes configured")
    return "\n".join(lines)


def show_lldp_neighbors() -> str:
    return "Port      Neighbor Device ID             Neighbor Port ID      TTL\nNo LLDP neighbors in the local single-device topology"


def show_spanning_tree(device: DeviceState) -> str:
    lines = [f"Spanning tree enabled protocol {device.spanning_tree_mode}"]
    for vlan_id in sorted(device.vlans):
        priority = device.spanning_tree_priorities.get(vlan_id, 32768)
        lines.extend([f"VLAN{vlan_id:04d}", f"  Root ID    Priority    {priority + vlan_id}", "  Interface        Role Sts Cost      Prio.Nbr Type"])
        for interface in device.interfaces.values():
            if interface.switchport_mode != "routed" and interface.admin_up:
                lines.append(f"  {short_interface(interface.name):<16} Desg FWD 20000     {interface.stp_port_priority}.1 Simulated")
    return "\n".join(lines)


def show_port_channel(device: DeviceState) -> str:
    groups: dict[int, list[Interface]] = {}
    for interface in device.interfaces.values():
        if interface.channel_group is not None:
            groups.setdefault(interface.channel_group, []).append(interface)
    if not groups:
        return "No port-channels configured"
    lines = ["Port-Channel       Protocol    Ports", "-------------------------------------------------------"]
    for group, members in sorted(groups.items()):
        mode = members[0].channel_mode or "on"
        protocol = "LACP(a)" if mode == "active" else ("LACP(p)" if mode == "passive" else "static")
        ports = " ".join(f"{short_interface(member.name)}(P+)" for member in members)
        lines.append(f"Po{group}(U)             {protocol:<11} {ports}")
    return "\n".join(lines)


def show_mlag(device: DeviceState) -> str:
    config = device.mlag
    complete = all((config.domain_id, config.local_interface, config.peer_address, config.peer_link)) and not config.shutdown
    return "\n".join(["MLAG Configuration:", f"domain-id         : {config.domain_id or 'not configured'}", f"local-interface   : {config.local_interface or 'not configured'}", f"peer-address      : {config.peer_address or 'not configured'}", f"peer-link         : {config.peer_link or 'not configured'}", "", "MLAG Status:", f"state             : {'Configured (no peer topology)' if complete else 'Inactive'}"])


def show_access_lists(device: DeviceState, name: str | None = None) -> str:
    acls: list[AccessList]
    if name:
        acls = [device.access_lists[name]] if name in device.access_lists else []
    else:
        acls = list(device.access_lists.values())
    if not acls:
        return "% Access list not found" if name else "No IP access lists configured"
    blocks = []
    for acl in acls:
        lines = [f"IP Access List {acl.name}"]
        lines.extend(f"        {entry}" for entry in acl.entries)
        lines.append(f"Total rules configured: {len(acl.entries)}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def show_policy_maps(device: DeviceState) -> str:
    if not device.policy_maps:
        return "No policy maps configured"
    lines: list[str] = []
    for policy in device.policy_maps.values():
        lines.append(f"Service-policy {policy.name}")
        for policy_class in policy.classes.values():
            lines.append(f"  Class-map: {policy_class.name} (match-any)")
            class_map = device.class_maps.get(policy_class.name)
            if class_map and class_map.access_group:
                lines.append(f"    Match: ip access-group name {class_map.access_group}")
            lines.extend(f"       {action}" for action in policy_class.actions)
    return "\n".join(lines)
