from __future__ import annotations

from .models.device import DeviceState, Interface


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
    for vlan_id, vlan in sorted(device.vlans.items()):
        if vlan_id == 1 and vlan.name == "default":
            continue
        lines.append(f"vlan {vlan_id}")
        if vlan.name:
            lines.append(f"   name {vlan.name}")
        lines.append("!")
    for interface in device.interfaces.values():
        if (
            not interface.description
            and interface.admin_up
            and interface.switchport_mode == "access"
            and interface.access_vlan == 1
            and interface.native_vlan == 1
            and interface.allowed_vlans is None
        ):
            continue
        lines.append(f"interface {interface.name}")
        if interface.description:
            lines.append(f"   description {interface.description}")
        lines.append(f"   switchport mode {interface.switchport_mode}")
        if interface.switchport_mode == "access":
            lines.append(f"   switchport access vlan {interface.access_vlan}")
        elif interface.allowed_vlans is not None:
            lines.append(f"   switchport trunk allowed vlan {_vlan_list(interface.allowed_vlans)}")
        if interface.switchport_mode == "trunk" and interface.native_vlan != 1:
            lines.append(f"   switchport trunk native vlan {interface.native_vlan}")
        if not interface.admin_up:
            lines.append("   shutdown")
        lines.append("!")
    lines.append("end")
    return "\n".join(lines)


def show_vlan(device: DeviceState, vlan_id: int | None = None) -> str:
    lines = [
        "VLAN  Name                             Status    Ports",
        "----- -------------------------------- --------- -------------------------------",
    ]
    vlans = device.vlans.items() if vlan_id is None else [(vlan_id, device.vlans[vlan_id])]
    for current_id, vlan in sorted(vlans):
        ports = [
            i.name.replace("Ethernet", "Et")
            for i in device.interfaces.values()
            if i.switchport_mode == "access" and i.access_vlan == current_id
        ]
        lines.append(f"{current_id:<5} {vlan.name or f'VLAN{current_id:04d}':<32} {'active':<9} {', '.join(ports)}".rstrip())
    return "\n".join(lines)


def show_switchport(interface: Interface) -> str:
    enabled = "Enabled"
    operational = "static access" if interface.switchport_mode == "access" else "trunk"
    return "\n".join(
        [
            f"Name: {interface.name.replace('Ethernet', 'Et')}",
            f"Switchport: {enabled}",
            f"Administrative Mode: {interface.switchport_mode}",
            f"Operational Mode: {operational}",
            f"Access Mode VLAN: {interface.access_vlan}",
            f"Trunking Native Mode VLAN: {interface.native_vlan}",
            "Trunking VLANs Enabled: "
            + ("ALL" if interface.allowed_vlans is None else _vlan_list(interface.allowed_vlans)),
        ]
    )


def show_interfaces_trunk(device: DeviceState, interface_name: str | None = None) -> str:
    interfaces = [
        interface
        for interface in device.interfaces.values()
        if interface.switchport_mode == "trunk"
        and (interface_name is None or interface.name == interface_name)
    ]
    if not interfaces:
        return "No trunk interfaces configured"
    lines = ["Port            Mode            Status          Native vlan"]
    for interface in interfaces:
        status = "trunking" if interface.admin_up else "notconnect"
        lines.append(
            f"{interface.name.replace('Ethernet', 'Et'):<15} "
            f"{'trunk':<15} {status:<15} {interface.native_vlan}"
        )
    lines.extend(["", "Port            Vlans allowed"])
    for interface in interfaces:
        allowed = "ALL" if interface.allowed_vlans is None else _vlan_list(interface.allowed_vlans)
        lines.append(f"{interface.name.replace('Ethernet', 'Et'):<15} {allowed}")
    lines.extend(["", "Port            Vlans allowed and active in management domain"])
    active = set(device.vlans)
    for interface in interfaces:
        permitted = active if interface.allowed_vlans is None else active & interface.allowed_vlans
        lines.append(f"{interface.name.replace('Ethernet', 'Et'):<15} {_vlan_list(permitted)}")
    return "\n".join(lines)


def show_interfaces_status(device: DeviceState, interface_name: str | None = None) -> str:
    interfaces = [
        interface
        for interface in device.interfaces.values()
        if interface_name is None or interface.name == interface_name
    ]
    lines = ["Port      Name               Status       Vlan  Duplex Speed Type"]
    for interface in interfaces:
        status = "connected" if interface.admin_up else "disabled"
        vlan = "trunk" if interface.switchport_mode == "trunk" else str(interface.access_vlan)
        lines.append(
            f"{interface.name.replace('Ethernet', 'Et'):<9} "
            f"{interface.description[:18]:<18} {status:<12} {vlan:<5} "
            f"{'full':<6} {'auto':<5} simulated"
        )
    return "\n".join(lines)


def show_interfaces_vlans(device: DeviceState, interface_name: str | None = None) -> str:
    interfaces = [
        interface
        for interface in device.interfaces.values()
        if interface_name is None or interface.name == interface_name
    ]
    lines = ["Port       Untagged Tagged"]
    for interface in interfaces:
        if interface.switchport_mode == "access":
            untagged, tagged = str(interface.access_vlan), "-"
        else:
            untagged = str(interface.native_vlan)
            if interface.allowed_vlans is None:
                tagged = "ALL"
            else:
                tagged = _vlan_list(interface.allowed_vlans - {interface.native_vlan})
        lines.append(f"{interface.name.replace('Ethernet', 'Et'):<10} {untagged:<8} {tagged}")
    return "\n".join(lines)
