from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field


@dataclass
class Vlan:
    vlan_id: int
    name: str = ""
    active: bool = True


@dataclass
class Interface:
    name: str
    description: str = ""
    admin_up: bool = True
    switchport_mode: str = "access"
    access_vlan: int = 1
    native_vlan: int = 1
    allowed_vlans: set[int] | None = None
    encapsulation_vlan: int | None = None
    ipv4_addresses: list[str] = field(default_factory=list)
    ipv6_addresses: list[str] = field(default_factory=list)
    channel_group: int | None = None
    channel_mode: str | None = None
    mlag_id: int | None = None
    stp_portfast: str = "auto"
    stp_port_priority: int = 128
    ip_access_groups: dict[str, str] = field(default_factory=dict)
    service_policies: dict[str, str] = field(default_factory=dict)
    autostate: bool = True

    @property
    def is_ethernet(self) -> bool:
        return self.name.startswith("Ethernet")

    @property
    def is_switchport_capable(self) -> bool:
        return self.name.startswith(("Ethernet", "Port-Channel")) and "." not in self.name


@dataclass
class StaticRoute:
    prefix: str
    next_hop: str


@dataclass
class AccessList:
    name: str
    entries: list[str] = field(default_factory=list)


@dataclass
class MlagConfig:
    domain_id: str = ""
    local_interface: str = ""
    peer_address: str = ""
    peer_link: str = ""
    shutdown: bool = False


@dataclass
class ClassMap:
    name: str
    access_group: str = ""


@dataclass
class PolicyClass:
    name: str
    actions: list[str] = field(default_factory=list)


@dataclass
class PolicyMap:
    name: str
    classes: dict[str, PolicyClass] = field(default_factory=dict)


@dataclass
class OspfProcess:
    process_id: int
    router_id: str = ""
    networks: list[tuple[str, str]] = field(default_factory=list)
    redistribute: set[str] = field(default_factory=set)


@dataclass
class ConfigSnapshot:
    state: "DeviceState"

    @property
    def hostname(self) -> str:
        return self.state.hostname


@dataclass
class DeviceState:
    hostname: str = "switch"
    vlans: dict[int, Vlan] = field(default_factory=lambda: {1: Vlan(1, "default")})
    interfaces: dict[str, Interface] = field(default_factory=dict)
    ip_routing: bool = False
    ipv6_unicast_routing: bool = False
    static_routes: list[StaticRoute] = field(default_factory=list)
    ipv6_static_routes: list[StaticRoute] = field(default_factory=list)
    spanning_tree_mode: str = "mstp"
    spanning_tree_priorities: dict[int, int] = field(default_factory=dict)
    rip_networks: list[str] = field(default_factory=list)
    rip_redistribute: set[str] = field(default_factory=set)
    ospf_processes: dict[int, OspfProcess] = field(default_factory=dict)
    access_lists: dict[str, AccessList] = field(default_factory=dict)
    control_plane_acl: str = "default-control-plane-acl"
    ssh_service_acl: str = ""
    mlag: MlagConfig = field(default_factory=MlagConfig)
    class_maps: dict[str, ClassMap] = field(default_factory=dict)
    policy_maps: dict[str, PolicyMap] = field(default_factory=dict)
    startup: ConfigSnapshot | None = None

    def __post_init__(self) -> None:
        if not self.interfaces:
            self.interfaces = {
                **{f"Ethernet{i}": Interface(f"Ethernet{i}") for i in range(1, 49)},
                "Management1": Interface("Management1", switchport_mode="routed"),
            }

    def ensure_vlan(self, vlan_id: int) -> Vlan:
        return self.vlans.setdefault(vlan_id, Vlan(vlan_id))

    def ensure_interface(self, name: str) -> Interface:
        if name not in self.interfaces:
            routed = name.startswith(("Vlan", "Loopback", "Management")) or "." in name
            self.interfaces[name] = Interface(name, switchport_mode="routed" if routed else "access")
        return self.interfaces[name]

    def expand_interfaces(self, selector: str) -> list[Interface]:
        if selector.startswith("Ethernet") and "-" in selector:
            first, last = selector.removeprefix("Ethernet").split("-", 1)
            return [self.ensure_interface(f"Ethernet{i}") for i in range(int(first), int(last) + 1)]
        return [self.ensure_interface(selector)]

    def ensure_access_list(self, name: str) -> AccessList:
        return self.access_lists.setdefault(name, AccessList(name))

    def ensure_class_map(self, name: str) -> ClassMap:
        return self.class_maps.setdefault(name, ClassMap(name))

    def ensure_policy_map(self, name: str) -> PolicyMap:
        return self.policy_maps.setdefault(name, PolicyMap(name))

    def save_startup(self) -> None:
        saved = deepcopy(self)
        saved.startup = None
        self.startup = ConfigSnapshot(saved)
