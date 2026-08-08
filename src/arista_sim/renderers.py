from __future__ import annotations

from .models.device import DeviceState, Interface


def _vlan_list(vlans: set[int]) -> str:
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
        if not interface.admin_up:
            lines.append("   shutdown")
        lines.append("!")
    lines.append("end")
    return "\n".join(lines)


def show_vlan(device: DeviceState) -> str:
    lines = [
        "VLAN  Name                             Status    Ports",
        "----- -------------------------------- --------- -------------------------------",
    ]
    for vlan_id, vlan in sorted(device.vlans.items()):
        ports = [
            i.name.replace("Ethernet", "Et")
            for i in device.interfaces.values()
            if i.switchport_mode == "access" and i.access_vlan == vlan_id
        ]
        lines.append(f"{vlan_id:<5} {vlan.name or f'VLAN{vlan_id:04d}':<32} {'active':<9} {', '.join(ports)}".rstrip())
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
            "Trunking VLANs Enabled: "
            + ("ALL" if interface.allowed_vlans is None else _vlan_list(interface.allowed_vlans)),
        ]
    )
