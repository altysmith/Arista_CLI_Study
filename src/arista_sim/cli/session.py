from __future__ import annotations

import re
import shlex
from enum import Enum
from ipaddress import IPv4Address, IPv6Address, ip_address, ip_interface, ip_network

from ..models.device import DeviceState, OspfProcess, PolicyClass, StaticRoute
from ..renderers import (
    running_config,
    short_interface,
    show_access_lists,
    show_interfaces_status,
    show_interfaces_trunk,
    show_interfaces_vlans,
    show_ip_interface_brief,
    show_ip_route,
    show_lldp_neighbors,
    show_mlag,
    show_policy_maps,
    show_port_channel,
    show_spanning_tree,
    show_switchport,
    show_vlan,
)
from .command_tree import CommandTree, argument, literal
from .errors import CliError


class Mode(str, Enum):
    EXEC = "exec"
    PRIVILEGED = "privileged"
    CONFIG = "config"
    VLAN = "vlan"
    INTERFACE = "interface"
    ROUTER_RIP = "router-rip"
    ROUTER_OSPF = "router-ospf"
    ACL = "acl"
    MLAG = "mlag"
    CONTROL_PLANE = "control-plane"
    MANAGEMENT_SSH = "management-ssh"
    CLASS_MAP = "class-map"
    POLICY_MAP = "policy-map"
    POLICY_CLASS = "policy-class"


def parse_word(token: str) -> str:
    if not token:
        raise ValueError
    return token


def parse_vlan(token: str) -> int:
    value = parse_number(token)
    if not 1 <= value <= 4094:
        raise ValueError
    return value


def parse_number(token: str) -> int:
    if not token.isdigit():
        raise ValueError
    return int(token)


def bounded_number(low: int, high: int, multiple: int = 1):
    def parser(token: str) -> int:
        value = parse_number(token)
        if not low <= value <= high or value % multiple:
            raise ValueError
        return value
    return parser


def parse_interface(token: str) -> str:
    compact = token.replace(" ", "")
    ethernet = re.fullmatch(r"(?i)(?:ethernet|et)(\d+)(?:-(\d+))?(?:\.(\d+))?", compact)
    if ethernet:
        first = int(ethernet.group(1))
        last = int(ethernet.group(2)) if ethernet.group(2) else None
        subinterface = ethernet.group(3)
        if not 1 <= first <= 48 or (last is not None and not first <= last <= 48) or (last and subinterface):
            raise ValueError
        suffix = f"-{last}" if last is not None else (f".{subinterface}" if subinterface else "")
        return f"Ethernet{first}{suffix}"
    patterns = (
        (r"(?i)(?:management|ma)(\d+)", "Management", 1, 1),
        (r"(?i)(?:vlan|vl)(\d+)", "Vlan", 1, 4094),
        (r"(?i)(?:port-channel|po)(\d+)", "Port-Channel", 1, 2000),
        (r"(?i)(?:loopback|lo)(\d+)", "Loopback", 0, 999),
    )
    for pattern, prefix, low, high in patterns:
        match = re.fullmatch(pattern, compact)
        if match and low <= int(match.group(1)) <= high:
            return f"{prefix}{int(match.group(1))}"
    raise ValueError


def parse_interface_number(kind: str):
    def parser(token: str) -> str:
        return parse_interface(f"{kind}{token}")
    return parser


def parse_vlan_list(token: str) -> set[int]:
    vlans: set[int] = set()
    for part in token.split(","):
        if not part:
            raise ValueError
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start, end = parse_vlan(start_text), parse_vlan(end_text)
            if start > end:
                raise ValueError
            vlans.update(range(start, end + 1))
        else:
            vlans.add(parse_vlan(part))
    return vlans


def parse_ipv4_interface(token: str) -> str:
    value = ip_interface(token)
    if not isinstance(value.ip, IPv4Address):
        raise ValueError
    return str(value)


def parse_ipv6_interface(token: str) -> str:
    value = ip_interface(token)
    if not isinstance(value.ip, IPv6Address):
        raise ValueError
    return str(value)


def parse_ipv4_prefix(token: str) -> str:
    value = ip_network(token, strict=False)
    if value.version != 4:
        raise ValueError
    return str(value)


def parse_ipv6_prefix(token: str) -> str:
    value = ip_network(token, strict=False)
    if value.version != 6:
        raise ValueError
    return str(value)


def parse_ipv4_address(token: str) -> str:
    value = ip_address(token)
    if value.version != 4:
        raise ValueError
    return str(value)


def parse_ipv6_address(token: str) -> str:
    value = ip_address(token)
    if value.version != 6:
        raise ValueError
    return str(value)


def parse_ospf_area(token: str) -> str:
    if token.isdigit():
        value = int(token)
        if not 0 <= value <= 4294967295:
            raise ValueError
        return str(IPv4Address(value))
    return parse_ipv4_address(token)


def parse_ipv4_route_hop(token: str) -> str:
    try:
        return parse_ipv4_address(token)
    except ValueError:
        return parse_interface(token)


def parse_ipv6_route_hop(token: str) -> str:
    try:
        return parse_ipv6_address(token)
    except ValueError:
        return parse_interface(token)


def parse_acl_tail(token: str) -> str:
    if not token.strip():
        raise ValueError
    return token.strip()


class Session:
    def __init__(self, device: DeviceState | None = None) -> None:
        self.device = device or DeviceState()
        self.mode = Mode.EXEC
        self.context: int | str | tuple[str, str] | None = None
        self.closed = False
        self.history: list[str] = []
        self._trees = self._build_trees()

    @property
    def prompt(self) -> str:
        host = self.device.hostname
        if self.mode == Mode.EXEC:
            return f"{host}>"
        if self.mode == Mode.PRIVILEGED:
            return f"{host}#"
        if self.mode == Mode.CONFIG:
            return f"{host}(config)#"
        if self.mode == Mode.VLAN:
            return f"{host}(config-vlan-{self.context})#"
        if self.mode == Mode.INTERFACE:
            return f"{host}(config-if-{short_interface(str(self.context))})#"
        if self.mode == Mode.ROUTER_RIP:
            return f"{host}(config-router-rip)#"
        if self.mode == Mode.ROUTER_OSPF:
            return f"{host}(config-router-ospf)#"
        if self.mode == Mode.ACL:
            return f"{host}(config-acl-{self.context})#"
        if self.mode == Mode.MLAG:
            return f"{host}(config-mlag)#"
        if self.mode == Mode.CONTROL_PLANE:
            return f"{host}(config-cp)#"
        if self.mode == Mode.MANAGEMENT_SSH:
            return f"{host}(config-mgmt-ssh)#"
        if self.mode == Mode.CLASS_MAP:
            return f"{host}(config-cmap-{self.context})#"
        if self.mode == Mode.POLICY_MAP:
            return f"{host}(config-pmap-{self.context})#"
        policy, policy_class = self.context  # type: ignore[misc]
        return f"{host}(config-pmap-c-{policy}-{policy_class})#"

    @staticmethod
    def _interface_paths() -> list[list[tuple]]:
        return [
            [argument("interface", "Interface name (for example Et1 or Vlan10)", parse_interface)],
            [literal("ethernet", "Ethernet interface"), argument("interface", "Interface number or range", parse_interface_number("Ethernet"))],
            [literal("management", "Management interface"), argument("interface", "Management interface number", parse_interface_number("Management"))],
            [literal("vlan", "VLAN interface"), argument("interface", "VLAN interface number", parse_interface_number("Vlan"))],
            [literal("port-channel", "Port-channel interface"), argument("interface", "Port-channel number", parse_interface_number("Port-Channel"))],
            [literal("loopback", "Loopback interface"), argument("interface", "Loopback number", parse_interface_number("Loopback"))],
        ]

    def _build_trees(self) -> dict[Mode, CommandTree]:
        trees = {mode: CommandTree() for mode in Mode}

        def add(mode: Mode, parts: list[tuple], handler):
            trees[mode].add(parts, handler)

        add(Mode.EXEC, [literal("enable", "Turn on privileged commands")], self._enable)
        add(Mode.EXEC, [literal("exit", "Exit from the EXEC")], self._close)
        add(Mode.EXEC, [literal("logout", "Exit from the EXEC")], self._close)
        add(Mode.EXEC, [literal("connect", "Open a terminal connection")], self._not_implemented)
        add(Mode.PRIVILEGED, [literal("disable", "Turn off privileged commands")], self._disable)
        add(Mode.PRIVILEGED, [literal("configure", "Enter configuration mode")], self._configure)
        add(Mode.PRIVILEGED, [literal("configure"), literal("terminal", "Configure from the terminal")], self._configure)
        add(Mode.PRIVILEGED, [literal("connect", "Open a terminal connection")], self._not_implemented)
        add(Mode.PRIVILEGED, [literal("exit", "Exit from the EXEC")], self._close)
        add(Mode.PRIVILEGED, [literal("logout", "Exit from the EXEC")], self._close)
        add(Mode.PRIVILEGED, [literal("copy", "Copy a configuration file"), literal("running-config", "Current configuration"), literal("startup-config", "Startup configuration")], self._save)
        add(Mode.PRIVILEGED, [literal("write", "Write running configuration")], self._save)

        for mode in Mode:
            self._add_show_commands(mode, add)
        for mode in (Mode.EXEC, Mode.PRIVILEGED):
            add(mode, [literal("ping", "Send ICMP echo requests"), argument("target", "IPv4 or IPv6 destination", parse_word)], self._reachability_unavailable)
            add(mode, [literal("traceroute", "Trace route to a destination"), argument("target", "IPv4 or IPv6 destination", parse_word)], self._reachability_unavailable)

        add(Mode.CONFIG, [literal("hostname", "Set system hostname"), argument("hostname", "System hostname", parse_word)], self._hostname)
        add(Mode.CONFIG, [literal("vlan", "VLAN configuration"), argument("vlan", "VLAN ID (1-4094)", parse_vlan)], self._vlan)
        add(Mode.CONFIG, [literal("no", "Negate a command"), literal("vlan", "Remove VLAN"), argument("vlan", "VLAN ID (2-4094)", parse_vlan)], self._no_vlan)
        for path in self._interface_paths():
            add(Mode.CONFIG, [literal("interface", "Select an interface"), *path], self._interface)
        add(Mode.CONFIG, [literal("ip", "IPv4 configuration"), literal("routing", "Enable IPv4 routing")], self._ip_routing)
        add(Mode.CONFIG, [literal("no", "Negate a command"), literal("ip"), literal("routing", "Disable IPv4 routing")], self._no_ip_routing)
        add(Mode.CONFIG, [literal("ipv6", "IPv6 configuration"), literal("unicast-routing", "Enable IPv6 routing")], self._ipv6_routing)
        add(Mode.CONFIG, [literal("no"), literal("ipv6"), literal("unicast-routing", "Disable IPv6 routing")], self._no_ipv6_routing)
        add(Mode.CONFIG, [literal("ip"), literal("route", "Configure IPv4 static route"), argument("prefix", "IPv4 destination prefix", parse_ipv4_prefix), argument("next_hop", "Next hop or interface", parse_ipv4_route_hop)], self._ip_route)
        add(Mode.CONFIG, [literal("no"), literal("ip"), literal("route"), argument("prefix", "IPv4 destination prefix", parse_ipv4_prefix), argument("next_hop", "Next hop or interface", parse_ipv4_route_hop)], self._no_ip_route)
        add(Mode.CONFIG, [literal("ipv6"), literal("route", "Configure IPv6 static route"), argument("prefix", "IPv6 destination prefix", parse_ipv6_prefix), argument("next_hop", "Next hop or interface", parse_ipv6_route_hop)], self._ipv6_route)
        add(Mode.CONFIG, [literal("no"), literal("ipv6"), literal("route"), argument("prefix", "IPv6 destination prefix", parse_ipv6_prefix), argument("next_hop", "Next hop or interface", parse_ipv6_route_hop)], self._no_ipv6_route)
        add(Mode.CONFIG, [literal("router", "Routing protocol configuration"), literal("rip", "Routing Information Protocol")], self._router_rip)
        add(Mode.CONFIG, [literal("router", "Routing protocol configuration"), literal("ospf", "Open Shortest Path First"), argument("process", "OSPF process ID", bounded_number(1, 65535))], self._router_ospf)
        for stp_mode in ("mstp", "rstp", "rapid-pvst"):
            add(Mode.CONFIG, [literal("spanning-tree", "Spanning-tree configuration"), literal("mode", "Select protocol mode"), literal(stp_mode, f"Use {stp_mode}")], self._stp_mode)
        add(Mode.CONFIG, [literal("spanning-tree"), literal("vlan", "VLAN spanning tree"), argument("vlan", "VLAN ID", parse_vlan), literal("priority", "Bridge priority"), argument("priority", "0-61440 in steps of 4096", bounded_number(0, 61440, 4096))], self._stp_priority)
        add(Mode.CONFIG, [literal("mlag", "MLAG configuration"), literal("configuration", "Enter MLAG configuration mode")], self._mlag_mode)
        add(Mode.CONFIG, [literal("ip"), literal("access-list", "IPv4 access list"), argument("name", "Access-list name", parse_word)], self._acl_mode)
        add(Mode.CONFIG, [literal("control-plane", "Control-plane configuration")], self._control_plane_mode)
        add(Mode.CONFIG, [literal("management", "Management services"), literal("ssh", "SSH server configuration")], self._management_ssh_mode)
        add(Mode.CONFIG, [literal("class-map", "QoS class map"), literal("type", "Class-map type"), literal("qos", "Quality of service"), literal("match-any", "Match any criterion"), argument("name", "Class-map name", parse_word)], self._class_map_mode)
        add(Mode.CONFIG, [literal("policy-map", "QoS policy map"), literal("type", "Policy-map type"), literal("quality-of-service", "Quality of service"), argument("name", "Policy-map name", parse_word)], self._policy_map_mode)

        add(Mode.VLAN, [literal("name", "Set VLAN name"), argument("name", "VLAN name", parse_word, greedy=True)], self._vlan_name)
        add(Mode.VLAN, [literal("no", "Negate a command"), literal("name", "Remove VLAN name")], self._no_vlan_name)

        self._add_interface_commands(add)
        self._add_rip_commands(add)
        self._add_ospf_commands(add)
        self._add_acl_commands(add)
        self._add_mlag_commands(add)
        self._add_qos_commands(add)
        add(Mode.CONTROL_PLANE, [literal("ip", "IPv4 configuration"), literal("access-group", "Apply control-plane ACL"), argument("name", "Access-list name", parse_word), literal("in", "Inbound traffic")], self._control_plane_acl)
        add(Mode.CONTROL_PLANE, [literal("no"), literal("ip"), literal("access-group", "Restore default control-plane ACL"), argument("name", "Access-list name", parse_word), literal("in")], self._no_control_plane_acl)
        add(Mode.MANAGEMENT_SSH, [literal("ip", "IPv4 configuration"), literal("access-group", "Apply SSH service ACL"), argument("name", "Access-list name", parse_word), literal("in", "Inbound connections")], self._ssh_acl)
        add(Mode.MANAGEMENT_SSH, [literal("no"), literal("ip"), literal("access-group", "Remove SSH service ACL"), argument("name", "Access-list name", parse_word), literal("in")], self._no_ssh_acl)

        config_modes = [mode for mode in Mode if mode not in (Mode.EXEC, Mode.PRIVILEGED)]
        for mode in config_modes:
            add(mode, [literal("end", "Exit to Privileged EXEC")], self._end)
            add(mode, [literal("exit", "Exit from current mode")], self._exit)
        return trees

    def _add_show_commands(self, mode: Mode, add) -> None:
        add(mode, [literal("show", "Show running system information"), literal("version", "Software and hardware version")], self._show_version)
        add(mode, [literal("show"), literal("vlan", "VLAN status")], self._show_vlan)
        add(mode, [literal("show"), literal("vlan"), argument("vlan", "VLAN ID (1-4094)", parse_vlan)], self._show_vlan)
        if mode != Mode.EXEC:
            add(mode, [literal("show"), literal("running-config", "Current operating configuration")], self._show_running)
            add(mode, [literal("show"), literal("startup-config", "Saved startup configuration")], self._show_startup)
        add(mode, [literal("show"), literal("interfaces", "Interface status and configuration")], self._show_interfaces_status)
        add(mode, [literal("show"), literal("interfaces"), literal("status", "Interface status")], self._show_interfaces_status)
        add(mode, [literal("show"), literal("interfaces"), literal("trunk", "Trunk status")], self._show_interfaces_trunk)
        add(mode, [literal("show"), literal("interfaces"), literal("vlans", "VLANs carried by interfaces")], self._show_interfaces_vlans)
        for path in self._interface_paths():
            add(mode, [literal("show"), literal("interfaces"), *path, literal("switchport", "Switchport information")], self._show_switchport)
            add(mode, [literal("show"), literal("interfaces"), *path, literal("status", "Interface status")], self._show_interfaces_status)
            add(mode, [literal("show"), literal("interfaces"), *path, literal("trunk", "Trunk status")], self._show_interfaces_trunk)
            add(mode, [literal("show"), literal("interfaces"), *path, literal("vlans", "VLANs carried")], self._show_interfaces_vlans)
        add(mode, [literal("show"), literal("ip", "IPv4 information"), literal("interface", "IPv4 interface information"), literal("brief", "Brief summary")], self._show_ip_interfaces)
        add(mode, [literal("show"), literal("ip"), literal("route", "IPv4 routing table")], self._show_ip_route)
        add(mode, [literal("show"), literal("ipv6", "IPv6 information"), literal("interface", "IPv6 interface information"), literal("brief", "Brief summary")], self._show_ipv6_interfaces)
        add(mode, [literal("show"), literal("ipv6"), literal("route", "IPv6 routing table")], self._show_ipv6_route)
        add(mode, [literal("show"), literal("arp", "ARP table")], self._show_arp)
        add(mode, [literal("show"), literal("ip"), literal("arp", "ARP table")], self._show_arp)
        add(mode, [literal("show"), literal("mac", "MAC information"), literal("address-table", "MAC address table")], self._show_mac)
        add(mode, [literal("show"), literal("lldp", "LLDP information"), literal("neighbors", "LLDP neighbors")], self._show_lldp)
        add(mode, [literal("show"), literal("lldp"), literal("neighbors"), literal("detail", "Detailed neighbor information")], self._show_lldp)
        add(mode, [literal("show"), literal("lldp"), literal("neighbors"), literal("detailed", "Detailed neighbor information")], self._show_lldp)
        add(mode, [literal("show"), literal("spanning-tree", "Spanning-tree state")], self._show_spanning_tree)
        add(mode, [literal("show"), literal("port-channel", "Port-channel members")], self._show_port_channel)
        add(mode, [literal("show"), literal("port-channel"), literal("dense", "Dense port-channel summary")], self._show_port_channel)
        add(mode, [literal("show"), literal("mlag", "MLAG configuration and status")], self._show_mlag)
        add(mode, [literal("show"), literal("ip"), literal("access-lists", "IPv4 access lists")], self._show_access_lists)
        add(mode, [literal("show"), literal("ip"), literal("access-lists"), argument("name", "Access-list name", parse_word)], self._show_access_lists)
        add(mode, [literal("show"), literal("management", "Management services"), literal("ssh", "SSH server"), literal("ip", "IPv4"), literal("access-list", "Service ACL")], self._show_ssh_acl)
        add(mode, [literal("show"), literal("policy-map", "QoS policy maps")], self._show_policy_maps)
        add(mode, [literal("show"), literal("ip"), literal("rip", "RIP information"), literal("database", "RIP database")], self._show_rip)
        add(mode, [literal("show"), literal("ip"), literal("rip"), literal("neighbors", "RIP neighbors")], self._show_rip)
        add(mode, [literal("show"), literal("ip"), literal("ospf", "OSPF information")], self._show_ospf)
        add(mode, [literal("show"), literal("ip"), literal("ospf"), literal("neighbor", "OSPF neighbors")], self._show_ospf_neighbors)
        add(mode, [literal("show"), literal("ip"), literal("ospf"), literal("interface", "OSPF interfaces"), literal("brief", "Brief summary")], self._show_ospf_interfaces)
        add(mode, [literal("show"), literal("ip"), literal("protocols", "Routing protocol status")], self._show_ip_protocols)

    def _add_interface_commands(self, add) -> None:
        mode = Mode.INTERFACE
        add(mode, [literal("description", "Interface description"), argument("description", "Description text", parse_word, greedy=True)], self._description)
        add(mode, [literal("no", "Negate a command"), literal("description", "Remove interface description")], self._no_description)
        add(mode, [literal("shutdown", "Administratively disable interface")], self._shutdown)
        add(mode, [literal("no"), literal("shutdown", "Administratively enable interface")], self._no_shutdown)
        add(mode, [literal("switchport", "Enable Layer 2 switching")], self._switchport)
        add(mode, [literal("no"), literal("switchport", "Configure routed interface")], self._no_switchport)
        add(mode, [literal("switchport"), literal("mode", "Set switching mode"), literal("access", "Access mode")], self._access_mode)
        add(mode, [literal("switchport"), literal("mode"), literal("trunk", "Trunk mode")], self._trunk_mode)
        add(mode, [literal("no"), literal("switchport"), literal("mode", "Restore access mode")], self._default_switchport_mode)
        add(mode, [literal("switchport"), literal("access", "Access parameters"), literal("vlan", "Set access VLAN"), argument("vlan", "VLAN ID", parse_vlan)], self._access_vlan)
        add(mode, [literal("no"), literal("switchport"), literal("access"), literal("vlan", "Restore VLAN 1")], self._default_access_vlan)
        trunk_allowed = [literal("switchport"), literal("trunk", "Trunk parameters"), literal("allowed", "Allowed VLANs"), literal("vlan", "Set allowed VLANs")]
        add(mode, [*trunk_allowed, literal("all", "All VLANs")], self._trunk_all)
        add(mode, [*trunk_allowed, literal("none", "No VLANs")], self._trunk_none)
        add(mode, [*trunk_allowed, literal("add", "Add VLANs"), argument("vlans", "VLAN list", parse_vlan_list)], self._trunk_add)
        add(mode, [*trunk_allowed, literal("remove", "Remove VLANs"), argument("vlans", "VLAN list", parse_vlan_list)], self._trunk_remove)
        add(mode, [*trunk_allowed, literal("except", "All except VLANs"), argument("vlans", "VLAN list", parse_vlan_list)], self._trunk_except)
        add(mode, [*trunk_allowed, argument("vlans", "VLAN list (for example 5,10-12)", parse_vlan_list)], self._trunk_allowed)
        add(mode, [literal("no"), *trunk_allowed], self._trunk_all)
        trunk_native = [literal("switchport"), literal("trunk"), literal("native", "Native VLAN"), literal("vlan", "Set native VLAN")]
        add(mode, [*trunk_native, argument("vlan", "VLAN ID", parse_vlan)], self._trunk_native)
        add(mode, [literal("no"), *trunk_native], self._default_trunk_native)
        add(mode, [literal("encapsulation", "Subinterface encapsulation"), literal("dot1q", "IEEE 802.1Q"), literal("vlan", "VLAN ID"), argument("vlan", "VLAN ID", parse_vlan)], self._encapsulation)
        add(mode, [literal("ip", "IPv4 interface configuration"), literal("address", "Assign IPv4 address"), argument("address", "IPv4/prefix", parse_ipv4_interface)], self._ip_address)
        add(mode, [literal("no"), literal("ip"), literal("address", "Remove IPv4 addresses")], self._no_ip_address)
        add(mode, [literal("ipv6", "IPv6 interface configuration"), literal("address", "Assign IPv6 address"), argument("address", "IPv6/prefix", parse_ipv6_interface)], self._ipv6_address)
        add(mode, [literal("no"), literal("ipv6"), literal("address", "Remove IPv6 addresses")], self._no_ipv6_address)
        for channel_mode in ("active", "passive", "on"):
            add(mode, [literal("channel-group", "Assign LACP/static channel group"), argument("group", "Port-channel ID", bounded_number(1, 2000)), literal("mode", "LACP mode"), literal(channel_mode, f"Use {channel_mode} mode")], self._channel_group)
        add(mode, [literal("no"), literal("channel-group", "Remove channel-group assignment")], self._no_channel_group)
        add(mode, [literal("mlag", "Assign MLAG ID"), argument("mlag_id", "MLAG ID", bounded_number(1, 2000))], self._interface_mlag)
        add(mode, [literal("no"), literal("mlag", "Remove MLAG ID")], self._no_interface_mlag)
        add(mode, [literal("spanning-tree", "Interface spanning-tree"), literal("portfast", "Enable PortFast")], self._portfast)
        for port_type in ("auto", "edge", "network", "normal"):
            add(mode, [literal("spanning-tree"), literal("portfast"), literal(port_type, f"Set {port_type} port type")], self._portfast)
        add(mode, [literal("no"), literal("spanning-tree"), literal("portfast", "Restore auto edge detection")], self._no_portfast)
        add(mode, [literal("spanning-tree"), literal("port-priority", "STP port priority"), argument("priority", "0-240 in steps of 16", bounded_number(0, 240, 16))], self._port_priority)
        for direction in ("in", "out"):
            add(mode, [literal("ip"), literal("access-group", "Apply IPv4 ACL"), argument("name", "Access-list name", parse_word), literal(direction, f"{direction}bound")], self._interface_acl)
            add(mode, [literal("ipv4"), literal("access-group", "Apply IPv4 ACL"), argument("name", "Access-list name", parse_word), literal(direction, f"{direction}bound")], self._interface_acl)
            add(mode, [literal("no"), literal("ip"), literal("access-group", "Remove IPv4 ACL"), argument("name", "Access-list name", parse_word), literal(direction)], self._no_interface_acl)
        for direction in ("input", "output"):
            add(mode, [literal("service-policy", "Apply QoS policy"), literal("type", "Policy type"), literal("qos", "Quality of service"), literal(direction, f"{direction} direction"), argument("name", "Policy-map name", parse_word)], self._service_policy)
            add(mode, [literal("no"), literal("service-policy"), literal("type"), literal("qos"), literal(direction), argument("name", "Policy-map name", parse_word)], self._no_service_policy)
        add(mode, [literal("no"), literal("autostate", "Disable SVI autostate")], self._no_autostate)
        add(mode, [literal("autostate", "Enable SVI autostate")], self._autostate)

    def _add_rip_commands(self, add) -> None:
        add(Mode.ROUTER_RIP, [literal("network", "Enable RIP on a network"), argument("network", "IPv4 network or address", parse_word)], self._rip_network)
        add(Mode.ROUTER_RIP, [literal("no"), literal("network", "Remove RIP network"), argument("network", "IPv4 network or address", parse_word)], self._no_rip_network)
        for source in ("connected", "static"):
            add(Mode.ROUTER_RIP, [literal("redistribute", "Redistribute routes"), literal(source, f"Redistribute {source} routes")], self._rip_redistribute)
            add(Mode.ROUTER_RIP, [literal("no"), literal("redistribute"), literal(source)], self._no_rip_redistribute)

    def _add_ospf_commands(self, add) -> None:
        add(Mode.ROUTER_OSPF, [literal("router-id", "Set OSPF router ID"), argument("router_id", "IPv4 router ID", parse_ipv4_address)], self._ospf_router_id)
        add(Mode.ROUTER_OSPF, [literal("network", "Assign network to an OSPF area"), argument("network", "IPv4 prefix in CIDR notation", parse_ipv4_prefix), literal("area", "OSPF area"), argument("area", "Area ID", parse_ospf_area)], self._ospf_network)
        add(Mode.ROUTER_OSPF, [literal("no"), literal("network", "Remove OSPF network"), argument("network", "IPv4 prefix in CIDR notation", parse_ipv4_prefix), literal("area"), argument("area", "Area ID", parse_ospf_area)], self._no_ospf_network)
        for source in ("connected", "static", "rip"):
            add(Mode.ROUTER_OSPF, [literal("redistribute", "Redistribute routes"), literal(source, f"Redistribute {source} routes")], self._ospf_redistribute)
            add(Mode.ROUTER_OSPF, [literal("no"), literal("redistribute"), literal(source)], self._no_ospf_redistribute)

    def _add_acl_commands(self, add) -> None:
        for action in ("permit", "deny"):
            add(Mode.ACL, [literal(action, f"{action.title()} matching traffic"), argument("rule", "Protocol, source, destination, and optional service", parse_acl_tail, greedy=True)], self._acl_entry)
            add(Mode.ACL, [argument("sequence", "Sequence number", bounded_number(1, 4294967295)), literal(action), argument("rule", "Protocol, source, destination, and optional service", parse_acl_tail, greedy=True)], self._acl_entry)
        add(Mode.ACL, [literal("remark", "ACL comment"), argument("remark", "Comment text", parse_acl_tail, greedy=True)], self._acl_remark)
        add(Mode.ACL, [literal("no"), argument("sequence", "Sequence number", bounded_number(1, 4294967295))], self._no_acl_sequence)

    def _add_mlag_commands(self, add) -> None:
        add(Mode.MLAG, [literal("domain-id", "MLAG domain ID"), argument("domain", "Domain identifier", parse_word)], self._mlag_domain)
        add(Mode.MLAG, [literal("local-interface", "MLAG local SVI"), literal("vlan", "VLAN interface"), argument("vlan", "VLAN ID", parse_vlan)], self._mlag_local)
        add(Mode.MLAG, [literal("peer-address", "MLAG peer IPv4 address"), argument("address", "Peer IPv4 address", parse_ipv4_address)], self._mlag_peer)
        add(Mode.MLAG, [literal("peer-link", "MLAG peer link"), literal("port-channel", "Port-channel interface"), argument("interface", "Port-channel ID", parse_interface_number("Port-Channel"))], self._mlag_peer_link)
        add(Mode.MLAG, [literal("shutdown", "Disable MLAG")], self._mlag_shutdown)
        add(Mode.MLAG, [literal("no"), literal("shutdown", "Enable MLAG")], self._no_mlag_shutdown)

    def _add_qos_commands(self, add) -> None:
        add(Mode.CLASS_MAP, [literal("match", "Match criterion"), literal("ip", "IPv4"), literal("access-group", "Match ACL"), argument("name", "Access-list name", parse_word)], self._class_match_acl)
        add(Mode.POLICY_MAP, [literal("class", "Policy class"), argument("name", "Class-map name or class-default", parse_word)], self._policy_class_mode)
        for keyword, parser in (("cos", bounded_number(0, 7)), ("dscp", bounded_number(0, 63)), ("traffic-class", bounded_number(0, 7))):
            add(Mode.POLICY_CLASS, [literal("set", "Set QoS field"), literal(keyword, f"Set {keyword}"), argument("value", "QoS value", parser)], self._policy_set)
        add(Mode.POLICY_CLASS, [literal("police", "Configure policer"), literal("cir", "Committed information rate"), argument("police", "Rate and optional burst parameters", parse_acl_tail, greedy=True)], self._policy_police)

    def execute(self, line: str) -> str:
        line = line.strip()
        if not line:
            return ""
        self.history.append(line)
        if "?" in line:
            return self.help(line)
        try:
            tokens = shlex.split(line)
        except ValueError:
            return "% Invalid input"
        try:
            return self._trees[self.mode].execute(tokens)
        except CliError as error:
            return error.message

    def help(self, line: str) -> str:
        before = line.split("?", 1)[0]
        trailing_space = bool(before) and before[-1].isspace()
        try:
            tokens = shlex.split(before)
            partial = "" if trailing_space else (tokens.pop() if tokens else "")
            return self._trees[self.mode].help(tokens, partial)
        except (CliError, ValueError) as error:
            return error.message if isinstance(error, CliError) else "% Invalid input"

    def complete(self, line: str) -> tuple[str, list[str]]:
        trailing_space = bool(line) and line[-1].isspace()
        tokens = line.split()
        partial = "" if trailing_space else (tokens.pop() if tokens else "")
        matches = self._trees[self.mode].complete(tokens, partial)
        if len(matches) == 1:
            prefix = " ".join(tokens)
            return f"{prefix} {matches[0]}".lstrip() + " ", matches
        return line, matches

    def _interfaces(self):
        return self.device.expand_interfaces(str(self.context))

    def _set_interfaces(self, attribute: str, value) -> None:
        for interface in self._interfaces():
            setattr(interface, attribute, value.copy() if isinstance(value, set) else value)

    def _enable(self, _: dict) -> str:
        self.mode = Mode.PRIVILEGED
        return ""

    def _disable(self, _: dict) -> str:
        self.mode = Mode.EXEC
        return ""

    def _configure(self, _: dict) -> str:
        self.mode = Mode.CONFIG
        return ""

    def _close(self, _: dict) -> str:
        self.closed = True
        return ""

    def _not_implemented(self, _: dict) -> str:
        return "% Command not implemented in this simulator"

    def _reachability_unavailable(self, _: dict) -> str:
        return "% No simulated peer topology; reachability cannot be determined"

    def _hostname(self, values: dict) -> str:
        hostname = str(values["hostname"])
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,62}", hostname):
            return "% Invalid hostname"
        self.device.hostname = hostname
        return ""

    def _vlan(self, values: dict) -> str:
        vlan_id = int(values["vlan"])
        self.device.ensure_vlan(vlan_id)
        self.mode, self.context = Mode.VLAN, vlan_id
        return ""

    def _vlan_name(self, values: dict) -> str:
        self.device.ensure_vlan(int(self.context)).name = str(values["name"])
        return ""

    def _no_vlan(self, values: dict) -> str:
        vlan_id = int(values["vlan"])
        if vlan_id == 1:
            return "% VLAN 1 cannot be removed"
        self.device.vlans.pop(vlan_id, None)
        return ""

    def _no_vlan_name(self, _: dict) -> str:
        self.device.ensure_vlan(int(self.context)).name = ""
        return ""

    def _interface(self, values: dict) -> str:
        selector = str(values["interface"])
        for interface in self.device.expand_interfaces(selector):
            if interface.name.startswith("Vlan"):
                self.device.ensure_vlan(int(interface.name.removeprefix("Vlan")))
        self.mode, self.context = Mode.INTERFACE, selector
        return ""

    def _description(self, values: dict) -> str:
        self._set_interfaces("description", str(values["description"]))
        return ""

    def _no_description(self, _: dict) -> str:
        self._set_interfaces("description", "")
        return ""

    def _shutdown(self, _: dict) -> str:
        self._set_interfaces("admin_up", False)
        return ""

    def _no_shutdown(self, _: dict) -> str:
        self._set_interfaces("admin_up", True)
        return ""

    def _switchport(self, _: dict) -> str:
        self._set_interfaces("switchport_mode", "access")
        return ""

    def _no_switchport(self, _: dict) -> str:
        self._set_interfaces("switchport_mode", "routed")
        return ""

    def _access_mode(self, _: dict) -> str:
        self._set_interfaces("switchport_mode", "access")
        return ""

    def _trunk_mode(self, _: dict) -> str:
        self._set_interfaces("switchport_mode", "trunk")
        return ""

    def _default_switchport_mode(self, _: dict) -> str:
        return self._access_mode({})

    def _access_vlan(self, values: dict) -> str:
        self._set_interfaces("access_vlan", int(values["vlan"]))
        return ""

    def _default_access_vlan(self, _: dict) -> str:
        self._set_interfaces("access_vlan", 1)
        return ""

    def _trunk_all(self, _: dict) -> str:
        self._set_interfaces("allowed_vlans", None)
        return ""

    def _trunk_none(self, _: dict) -> str:
        self._set_interfaces("allowed_vlans", set())
        return ""

    def _trunk_add(self, values: dict) -> str:
        for interface in self._interfaces():
            if interface.allowed_vlans is not None:
                interface.allowed_vlans.update(values["vlans"])
        return ""

    def _trunk_remove(self, values: dict) -> str:
        for interface in self._interfaces():
            current = set(range(1, 4095)) if interface.allowed_vlans is None else set(interface.allowed_vlans)
            interface.allowed_vlans = current - set(values["vlans"])
        return ""

    def _trunk_except(self, values: dict) -> str:
        self._set_interfaces("allowed_vlans", set(range(1, 4095)) - set(values["vlans"]))
        return ""

    def _trunk_allowed(self, values: dict) -> str:
        self._set_interfaces("allowed_vlans", set(values["vlans"]))
        return ""

    def _trunk_native(self, values: dict) -> str:
        self._set_interfaces("native_vlan", int(values["vlan"]))
        return ""

    def _default_trunk_native(self, _: dict) -> str:
        self._set_interfaces("native_vlan", 1)
        return ""

    def _encapsulation(self, values: dict) -> str:
        self._set_interfaces("encapsulation_vlan", int(values["vlan"]))
        return ""

    def _ip_address(self, values: dict) -> str:
        for interface in self._interfaces():
            address = str(values["address"])
            if address not in interface.ipv4_addresses:
                interface.ipv4_addresses.append(address)
        return ""

    def _no_ip_address(self, _: dict) -> str:
        self._set_interfaces("ipv4_addresses", [])
        return ""

    def _ipv6_address(self, values: dict) -> str:
        for interface in self._interfaces():
            address = str(values["address"])
            if address not in interface.ipv6_addresses:
                interface.ipv6_addresses.append(address)
        return ""

    def _no_ipv6_address(self, _: dict) -> str:
        self._set_interfaces("ipv6_addresses", [])
        return ""

    def _channel_group(self, values: dict) -> str:
        group = int(values["group"])
        command = self.history[-1].lower()
        channel_mode = next(mode for mode in ("active", "passive", "on") if command.endswith(mode))
        self._set_interfaces("channel_group", group)
        self._set_interfaces("channel_mode", channel_mode)
        self.device.ensure_interface(f"Port-Channel{group}")
        return ""

    def _no_channel_group(self, _: dict) -> str:
        self._set_interfaces("channel_group", None)
        self._set_interfaces("channel_mode", None)
        return ""

    def _interface_mlag(self, values: dict) -> str:
        self._set_interfaces("mlag_id", int(values["mlag_id"]))
        return ""

    def _no_interface_mlag(self, _: dict) -> str:
        self._set_interfaces("mlag_id", None)
        return ""

    def _portfast(self, _: dict) -> str:
        final = self.history[-1].split()[-1].lower()
        self._set_interfaces("stp_portfast", "enabled" if final == "portfast" else final)
        return ""

    def _no_portfast(self, _: dict) -> str:
        self._set_interfaces("stp_portfast", "auto")
        return ""

    def _port_priority(self, values: dict) -> str:
        self._set_interfaces("stp_port_priority", int(values["priority"]))
        return ""

    def _interface_acl(self, values: dict) -> str:
        direction = self.history[-1].split()[-1].lower()
        for interface in self._interfaces():
            interface.ip_access_groups[direction] = str(values["name"])
        return ""

    def _no_interface_acl(self, values: dict) -> str:
        direction = self.history[-1].split()[-1].lower()
        for interface in self._interfaces():
            interface.ip_access_groups.pop(direction, None)
        return ""

    def _service_policy(self, values: dict) -> str:
        direction = self.history[-1].split()[-2].lower()
        for interface in self._interfaces():
            interface.service_policies[direction] = str(values["name"])
        return ""

    def _no_service_policy(self, values: dict) -> str:
        direction = self.history[-1].split()[-2].lower()
        for interface in self._interfaces():
            interface.service_policies.pop(direction, None)
        return ""

    def _no_autostate(self, _: dict) -> str:
        self._set_interfaces("autostate", False)
        return ""

    def _autostate(self, _: dict) -> str:
        self._set_interfaces("autostate", True)
        return ""

    def _ip_routing(self, _: dict) -> str:
        self.device.ip_routing = True
        return ""

    def _no_ip_routing(self, _: dict) -> str:
        self.device.ip_routing = False
        return ""

    def _ipv6_routing(self, _: dict) -> str:
        self.device.ipv6_unicast_routing = True
        return ""

    def _no_ipv6_routing(self, _: dict) -> str:
        self.device.ipv6_unicast_routing = False
        return ""

    def _add_route(self, values: dict, ipv6: bool = False) -> str:
        routes = self.device.ipv6_static_routes if ipv6 else self.device.static_routes
        route = StaticRoute(str(values["prefix"]), str(values["next_hop"]))
        if route not in routes:
            routes.append(route)
        return ""

    def _remove_route(self, values: dict, ipv6: bool = False) -> str:
        routes = self.device.ipv6_static_routes if ipv6 else self.device.static_routes
        target = StaticRoute(str(values["prefix"]), str(values["next_hop"]))
        routes[:] = [route for route in routes if route != target]
        return ""

    def _ip_route(self, values: dict) -> str:
        return self._add_route(values)

    def _no_ip_route(self, values: dict) -> str:
        return self._remove_route(values)

    def _ipv6_route(self, values: dict) -> str:
        return self._add_route(values, True)

    def _no_ipv6_route(self, values: dict) -> str:
        return self._remove_route(values, True)

    def _router_rip(self, _: dict) -> str:
        self.mode, self.context = Mode.ROUTER_RIP, None
        return ""

    def _rip_network(self, values: dict) -> str:
        network = str(values["network"])
        try:
            ip_network(network, strict=False)
        except ValueError:
            return "% Invalid input"
        if network not in self.device.rip_networks:
            self.device.rip_networks.append(network)
        return ""

    def _no_rip_network(self, values: dict) -> str:
        network = str(values["network"])
        self.device.rip_networks = [item for item in self.device.rip_networks if item != network]
        return ""

    def _rip_redistribute(self, _: dict) -> str:
        self.device.rip_redistribute.add(self.history[-1].split()[-1].lower())
        return ""

    def _no_rip_redistribute(self, _: dict) -> str:
        self.device.rip_redistribute.discard(self.history[-1].split()[-1].lower())
        return ""

    def _router_ospf(self, values: dict) -> str:
        process_id = int(values["process"])
        self.device.ospf_processes.setdefault(process_id, OspfProcess(process_id))
        self.mode, self.context = Mode.ROUTER_OSPF, process_id
        return ""

    def _ospf_router_id(self, values: dict) -> str:
        self.device.ospf_processes[int(self.context)].router_id = str(values["router_id"])
        return ""

    def _ospf_network(self, values: dict) -> str:
        process = self.device.ospf_processes[int(self.context)]
        assignment = (str(values["network"]), str(values["area"]))
        if assignment not in process.networks:
            process.networks.append(assignment)
        return ""

    def _no_ospf_network(self, values: dict) -> str:
        process = self.device.ospf_processes[int(self.context)]
        assignment = (str(values["network"]), str(values["area"]))
        process.networks = [item for item in process.networks if item != assignment]
        return ""

    def _ospf_redistribute(self, _: dict) -> str:
        self.device.ospf_processes[int(self.context)].redistribute.add(self.history[-1].split()[-1].lower())
        return ""

    def _no_ospf_redistribute(self, _: dict) -> str:
        self.device.ospf_processes[int(self.context)].redistribute.discard(self.history[-1].split()[-1].lower())
        return ""

    def _stp_mode(self, _: dict) -> str:
        self.device.spanning_tree_mode = self.history[-1].split()[-1].lower()
        return ""

    def _stp_priority(self, values: dict) -> str:
        self.device.spanning_tree_priorities[int(values["vlan"])] = int(values["priority"])
        return ""

    def _acl_mode(self, values: dict) -> str:
        name = str(values["name"])
        self.device.ensure_access_list(name)
        self.mode, self.context = Mode.ACL, name
        return ""

    def _acl_entry(self, values: dict) -> str:
        acl = self.device.ensure_access_list(str(self.context))
        action = next(word for word in self.history[-1].split() if word.lower() in ("permit", "deny")).lower()
        sequence = int(values.get("sequence", ((len(acl.entries) + 1) * 10)))
        acl.entries = [entry for entry in acl.entries if not entry.startswith(f"{sequence} ")]
        acl.entries.append(f"{sequence} {action} {values['rule']}")
        acl.entries.sort(key=lambda entry: int(entry.split()[0]))
        return ""

    def _acl_remark(self, values: dict) -> str:
        acl = self.device.ensure_access_list(str(self.context))
        sequence = (len(acl.entries) + 1) * 10
        acl.entries.append(f"{sequence} remark {values['remark']}")
        return ""

    def _no_acl_sequence(self, values: dict) -> str:
        sequence = int(values["sequence"])
        acl = self.device.ensure_access_list(str(self.context))
        acl.entries = [entry for entry in acl.entries if not entry.startswith(f"{sequence} ")]
        return ""

    def _control_plane_mode(self, _: dict) -> str:
        self.mode, self.context = Mode.CONTROL_PLANE, None
        return ""

    def _control_plane_acl(self, values: dict) -> str:
        self.device.control_plane_acl = str(values["name"])
        return ""

    def _no_control_plane_acl(self, _: dict) -> str:
        self.device.control_plane_acl = "default-control-plane-acl"
        return ""

    def _management_ssh_mode(self, _: dict) -> str:
        self.mode, self.context = Mode.MANAGEMENT_SSH, None
        return ""

    def _ssh_acl(self, values: dict) -> str:
        self.device.ssh_service_acl = str(values["name"])
        return ""

    def _no_ssh_acl(self, _: dict) -> str:
        self.device.ssh_service_acl = ""
        return ""

    def _mlag_mode(self, _: dict) -> str:
        self.mode, self.context = Mode.MLAG, None
        return ""

    def _mlag_domain(self, values: dict) -> str:
        self.device.mlag.domain_id = str(values["domain"])
        return ""

    def _mlag_local(self, values: dict) -> str:
        self.device.mlag.local_interface = f"Vlan{values['vlan']}"
        return ""

    def _mlag_peer(self, values: dict) -> str:
        self.device.mlag.peer_address = str(values["address"])
        return ""

    def _mlag_peer_link(self, values: dict) -> str:
        self.device.mlag.peer_link = str(values["interface"])
        return ""

    def _mlag_shutdown(self, _: dict) -> str:
        self.device.mlag.shutdown = True
        return ""

    def _no_mlag_shutdown(self, _: dict) -> str:
        self.device.mlag.shutdown = False
        return ""

    def _class_map_mode(self, values: dict) -> str:
        name = str(values["name"])
        self.device.ensure_class_map(name)
        self.mode, self.context = Mode.CLASS_MAP, name
        return ""

    def _class_match_acl(self, values: dict) -> str:
        self.device.ensure_class_map(str(self.context)).access_group = str(values["name"])
        return ""

    def _policy_map_mode(self, values: dict) -> str:
        name = str(values["name"])
        self.device.ensure_policy_map(name)
        self.mode, self.context = Mode.POLICY_MAP, name
        return ""

    def _policy_class_mode(self, values: dict) -> str:
        policy = str(self.context)
        class_name = str(values["name"])
        self.device.ensure_policy_map(policy).classes.setdefault(class_name, PolicyClass(class_name))
        self.mode, self.context = Mode.POLICY_CLASS, (policy, class_name)
        return ""

    def _policy_set(self, values: dict) -> str:
        policy, class_name = self.context  # type: ignore[misc]
        keyword = self.history[-1].split()[-2].lower()
        policy_class = self.device.policy_maps[policy].classes[class_name]
        policy_class.actions = [action for action in policy_class.actions if not action.startswith(f"set {keyword} ")]
        policy_class.actions.append(f"set {keyword} {values['value']}")
        return ""

    def _policy_police(self, values: dict) -> str:
        policy, class_name = self.context  # type: ignore[misc]
        policy_class = self.device.policy_maps[policy].classes[class_name]
        policy_class.actions = [action for action in policy_class.actions if not action.startswith("police cir ")]
        policy_class.actions.append(f"police cir {values['police']}")
        return ""

    def _end(self, _: dict) -> str:
        self.mode, self.context = Mode.PRIVILEGED, None
        return ""

    def _exit(self, _: dict) -> str:
        if self.mode == Mode.POLICY_CLASS:
            policy, _ = self.context  # type: ignore[misc]
            self.mode, self.context = Mode.POLICY_MAP, policy
        elif self.mode == Mode.CONFIG:
            self.mode, self.context = Mode.PRIVILEGED, None
        else:
            self.mode, self.context = Mode.CONFIG, None
        return ""

    def _show_version(self, _: dict) -> str:
        return "Arista EOS Network Foundations Simulator\nBehavioral training build (not an EOS image or hardware emulator)"

    def _show_vlan(self, values: dict) -> str:
        vlan_id = values.get("vlan")
        if vlan_id is not None and int(vlan_id) not in self.device.vlans:
            return f"% VLAN {vlan_id} not found"
        return show_vlan(self.device, int(vlan_id) if vlan_id is not None else None)

    def _show_running(self, _: dict) -> str:
        return running_config(self.device)

    def _show_startup(self, _: dict) -> str:
        return "% Startup configuration has not been saved" if self.device.startup is None else running_config(self.device.startup.state)

    def _show_switchport(self, values: dict) -> str:
        name = str(values["interface"])
        if "-" in name:
            return "% Interface ranges are not valid for this show command"
        return show_switchport(self.device.ensure_interface(name))

    def _show_interfaces_trunk(self, values: dict) -> str:
        name = values.get("interface")
        return show_interfaces_trunk(self.device, str(name) if name else None)

    def _show_interfaces_status(self, values: dict) -> str:
        name = values.get("interface")
        return show_interfaces_status(self.device, str(name) if name else None)

    def _show_interfaces_vlans(self, values: dict) -> str:
        name = values.get("interface")
        return show_interfaces_vlans(self.device, str(name) if name else None)

    def _show_ip_interfaces(self, _: dict) -> str:
        return show_ip_interface_brief(self.device)

    def _show_ipv6_interfaces(self, _: dict) -> str:
        return show_ip_interface_brief(self.device, True)

    def _show_ip_route(self, _: dict) -> str:
        return show_ip_route(self.device)

    def _show_ipv6_route(self, _: dict) -> str:
        return show_ip_route(self.device, True)

    def _show_arp(self, _: dict) -> str:
        return "Address         Age (min)  Hardware Addr   Interface\nNo ARP entries in the local single-device topology"

    def _show_mac(self, _: dict) -> str:
        return "Vlan    Mac Address       Type        Ports\nNo dynamically learned MAC addresses in the local single-device topology"

    def _show_lldp(self, _: dict) -> str:
        return show_lldp_neighbors()

    def _show_spanning_tree(self, _: dict) -> str:
        return show_spanning_tree(self.device)

    def _show_port_channel(self, _: dict) -> str:
        return show_port_channel(self.device)

    def _show_mlag(self, _: dict) -> str:
        return show_mlag(self.device)

    def _show_access_lists(self, values: dict) -> str:
        return show_access_lists(self.device, str(values["name"]) if values.get("name") else None)

    def _show_ssh_acl(self, _: dict) -> str:
        return f"SSH IPv4 service ACL: {self.device.ssh_service_acl or 'not configured'}"

    def _show_policy_maps(self, _: dict) -> str:
        return show_policy_maps(self.device)

    def _show_rip(self, _: dict) -> str:
        return "RIP is configured; no neighbors exist in the local single-device topology" if self.device.rip_networks else "RIP is not configured"

    def _show_ospf(self, _: dict) -> str:
        if not self.device.ospf_processes:
            return "OSPF is not configured"
        blocks = []
        for process in self.device.ospf_processes.values():
            area_count = len({area for _, area in process.networks})
            blocks.append(f"OSPF Routing Process {process.process_id} with ID {process.router_id or '0.0.0.0'}\n  Number of areas: {area_count}")
        return "\n\n".join(blocks)

    def _show_ospf_neighbors(self, _: dict) -> str:
        if not self.device.ospf_processes:
            return "OSPF is not configured"
        return "Neighbor ID     Pri   State      Address         Interface\nNo OSPF neighbors in the local single-device topology"

    def _show_ospf_interfaces(self, _: dict) -> str:
        if not self.device.ospf_processes:
            return "OSPF is not configured"
        lines = ["Interface        PID   Area        IP Address          State Nbrs"]
        for process in self.device.ospf_processes.values():
            for network, area in process.networks:
                lines.append(f"(network)        {process.process_id:<5} {area:<11} {network:<19} Sim   0")
        return "\n".join(lines)

    def _show_ip_protocols(self, _: dict) -> str:
        blocks = []
        if self.device.rip_networks:
            networks = ", ".join(self.device.rip_networks)
            blocks.append(f"Routing Protocol is 'rip'\n  Routing for Networks:\n    {networks}")
        for process in self.device.ospf_processes.values():
            networks = ", ".join(network for network, _ in process.networks) or "none"
            blocks.append(f"Routing Protocol is 'ospf {process.process_id}'\n  Router ID {process.router_id or '0.0.0.0'}\n  Routing for Networks:\n    {networks}")
        if not blocks:
            return "No dynamic routing protocol configured"
        return "\n\n".join(blocks)

    def _save(self, _: dict) -> str:
        self.device.save_startup()
        return "Copy completed successfully."
