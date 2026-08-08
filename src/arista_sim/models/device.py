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
    allowed_vlans: set[int] | None = None


@dataclass
class ConfigSnapshot:
    hostname: str
    vlans: dict[int, Vlan]
    interfaces: dict[str, Interface]


@dataclass
class DeviceState:
    hostname: str = "switch"
    vlans: dict[int, Vlan] = field(default_factory=lambda: {1: Vlan(1, "default")})
    interfaces: dict[str, Interface] = field(
        default_factory=lambda: {f"Ethernet{i}": Interface(f"Ethernet{i}") for i in range(1, 49)}
    )
    startup: ConfigSnapshot | None = None

    def ensure_vlan(self, vlan_id: int) -> Vlan:
        return self.vlans.setdefault(vlan_id, Vlan(vlan_id))

    def save_startup(self) -> None:
        self.startup = ConfigSnapshot(
            hostname=self.hostname,
            vlans=deepcopy(self.vlans),
            interfaces=deepcopy(self.interfaces),
        )
