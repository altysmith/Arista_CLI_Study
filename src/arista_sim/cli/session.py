from __future__ import annotations

import re
import shlex
from enum import Enum

from ..models.device import DeviceState
from ..renderers import (
    running_config,
    show_interfaces_status,
    show_interfaces_trunk,
    show_interfaces_vlans,
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


def parse_word(token: str) -> str:
    if not token:
        raise ValueError
    return token


def parse_vlan(token: str) -> int:
    try:
        value = int(token)
    except ValueError as exc:
        raise ValueError from exc
    if not 1 <= value <= 4094:
        raise ValueError
    return value


def parse_interface(token: str) -> str:
    match = re.fullmatch(r"(?i)(?:ethernet|et)(\d+)", token)
    if not match:
        raise ValueError
    number = int(match.group(1))
    if not 1 <= number <= 48:
        raise ValueError
    return f"Ethernet{number}"


def parse_interface_number(token: str) -> str:
    if not token.isdigit():
        raise ValueError
    return parse_interface(f"Et{token}")


def parse_vlan_list(token: str) -> set[int]:
    vlans: set[int] = set()
    for part in token.split(","):
        if not part:
            raise ValueError
        if "-" in part:
            bounds = part.split("-", 1)
            if len(bounds) != 2:
                raise ValueError
            start, end = parse_vlan(bounds[0]), parse_vlan(bounds[1])
            if start > end:
                raise ValueError
            vlans.update(range(start, end + 1))
        else:
            vlans.add(parse_vlan(part))
    return vlans


class Session:
    def __init__(self, device: DeviceState | None = None) -> None:
        self.device = device or DeviceState()
        self.mode = Mode.EXEC
        self.context: int | str | None = None
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
        short = str(self.context).replace("Ethernet", "Et")
        return f"{host}(config-if-{short})#"

    def _build_trees(self) -> dict[Mode, CommandTree]:
        trees = {mode: CommandTree() for mode in Mode}

        def add(mode: Mode, parts: list[tuple], handler):
            trees[mode].add(parts, handler)

        add(Mode.EXEC, [literal("enable", "Turn on privileged commands")], self._enable)
        add(Mode.EXEC, [literal("exit", "Exit from the EXEC")], self._close)
        add(Mode.EXEC, [literal("logout", "Exit from the EXEC")], self._close)
        # connect intentionally makes `con` ambiguous in privileged EXEC, matching EOS docs.
        add(Mode.EXEC, [literal("connect", "Open a terminal connection")], self._not_implemented)
        add(Mode.EXEC, [literal("show", "Show running system information"), literal("vlan", "VLAN status")], self._show_vlan)
        add(Mode.EXEC, [literal("show"), literal("vlan"), argument("vlan", "VLAN ID (1-4094)", parse_vlan)], self._show_vlan)
        add(Mode.EXEC, [literal("show"), literal("interfaces", "Interface status and configuration"), literal("status", "Interface status")], self._show_interfaces_status)
        add(Mode.EXEC, [literal("show"), literal("interfaces"), literal("trunk", "Trunk status")], self._show_interfaces_trunk)
        add(Mode.EXEC, [literal("show"), literal("interfaces"), literal("vlans", "VLANs carried by interfaces")], self._show_interfaces_vlans)
        for iface_parts in (
            [argument("interface", "Ethernet interface", parse_interface)],
            [literal("ethernet", "Ethernet interface"), argument("interface", "Interface number", parse_interface_number)],
        ):
            add(Mode.EXEC, [literal("show"), literal("interfaces"), *iface_parts, literal("switchport", "Switchport information")], self._show_switchport)
            add(Mode.EXEC, [literal("show"), literal("interfaces"), *iface_parts, literal("status", "Interface status")], self._show_interfaces_status)
            add(Mode.EXEC, [literal("show"), literal("interfaces"), *iface_parts, literal("trunk", "Trunk status")], self._show_interfaces_trunk)
            add(Mode.EXEC, [literal("show"), literal("interfaces"), *iface_parts, literal("vlans", "VLANs carried")], self._show_interfaces_vlans)

        add(Mode.PRIVILEGED, [literal("disable", "Turn off privileged commands")], self._disable)
        add(Mode.PRIVILEGED, [literal("configure", "Enter configuration mode")], self._configure)
        add(Mode.PRIVILEGED, [literal("configure"), literal("terminal", "Configure from the terminal")], self._configure)
        add(Mode.PRIVILEGED, [literal("connect", "Open a terminal connection")], self._not_implemented)
        add(Mode.PRIVILEGED, [literal("exit", "Exit from the EXEC")], self._close)
        add(Mode.PRIVILEGED, [literal("logout", "Exit from the EXEC")], self._close)
        add(Mode.PRIVILEGED, [literal("show", "Show running system information"), literal("vlan", "VLAN status")], self._show_vlan)
        add(Mode.PRIVILEGED, [literal("show"), literal("vlan"), argument("vlan", "VLAN ID (1-4094)", parse_vlan)], self._show_vlan)
        add(Mode.PRIVILEGED, [literal("show"), literal("running-config", "Current operating configuration")], self._show_running)
        add(Mode.PRIVILEGED, [literal("show"), literal("interfaces", "Interface status and configuration"), literal("status", "Interface status")], self._show_interfaces_status)
        add(Mode.PRIVILEGED, [literal("show"), literal("interfaces"), literal("trunk", "Trunk status")], self._show_interfaces_trunk)
        add(Mode.PRIVILEGED, [literal("show"), literal("interfaces"), literal("vlans", "VLANs carried by interfaces")], self._show_interfaces_vlans)
        for iface_parts in (
            [argument("interface", "Ethernet interface", parse_interface)],
            [literal("ethernet", "Ethernet interface"), argument("interface", "Interface number", parse_interface_number)],
        ):
            add(Mode.PRIVILEGED, [literal("show"), literal("interfaces", "Interface status and configuration"), *iface_parts, literal("switchport", "Switchport information")], self._show_switchport)
            add(Mode.PRIVILEGED, [literal("show"), literal("interfaces"), *iface_parts, literal("status", "Interface status")], self._show_interfaces_status)
            add(Mode.PRIVILEGED, [literal("show"), literal("interfaces"), *iface_parts, literal("trunk", "Trunk status")], self._show_interfaces_trunk)
            add(Mode.PRIVILEGED, [literal("show"), literal("interfaces"), *iface_parts, literal("vlans", "VLANs carried")], self._show_interfaces_vlans)
        add(Mode.PRIVILEGED, [literal("copy", "Copy a configuration file"), literal("running-config", "Current configuration"), literal("startup-config", "Startup configuration")], self._save)
        add(Mode.PRIVILEGED, [literal("write", "Write running configuration")], self._save)

        add(Mode.CONFIG, [literal("hostname", "Set system hostname"), argument("hostname", "System hostname", parse_word)], self._hostname)
        add(Mode.CONFIG, [literal("vlan", "VLAN configuration"), argument("vlan", "VLAN ID (1-4094)", parse_vlan)], self._vlan)
        add(Mode.CONFIG, [literal("no", "Negate a command"), literal("vlan", "Remove VLAN"), argument("vlan", "VLAN ID (2-4094)", parse_vlan)], self._no_vlan)
        for iface_parts in (
            [argument("interface", "Interface name (for example Et1)", parse_interface)],
            [literal("ethernet", "Ethernet interface"), argument("interface", "Interface number", parse_interface_number)],
        ):
            add(Mode.CONFIG, [literal("interface", "Select an interface"), *iface_parts], self._interface)

        add(Mode.VLAN, [literal("name", "Set VLAN name"), argument("name", "VLAN name", parse_word, greedy=True)], self._vlan_name)
        add(Mode.VLAN, [literal("no", "Negate a command"), literal("name", "Remove VLAN name")], self._no_vlan_name)
        add(Mode.INTERFACE, [literal("description", "Interface description"), argument("description", "Description text", parse_word, greedy=True)], self._description)
        add(Mode.INTERFACE, [literal("no", "Negate a command"), literal("description", "Remove interface description")], self._no_description)
        add(Mode.INTERFACE, [literal("shutdown", "Administratively disable interface")], self._shutdown)
        add(Mode.INTERFACE, [literal("no", "Negate a command"), literal("shutdown", "Administratively enable interface")], self._no_shutdown)
        add(Mode.INTERFACE, [literal("switchport", "Switchport configuration"), literal("mode", "Set switching mode"), literal("access", "Access mode")], self._access_mode)
        add(Mode.INTERFACE, [literal("switchport"), literal("mode"), literal("trunk", "Trunk mode")], self._trunk_mode)
        add(Mode.INTERFACE, [literal("no"), literal("switchport"), literal("mode", "Restore access mode")], self._default_switchport_mode)
        add(Mode.INTERFACE, [literal("switchport"), literal("access", "Access parameters"), literal("vlan", "Set access VLAN"), argument("vlan", "VLAN ID (1-4094)", parse_vlan)], self._access_vlan)
        add(Mode.INTERFACE, [literal("no"), literal("switchport"), literal("access"), literal("vlan", "Restore VLAN 1")], self._default_access_vlan)
        trunk_allowed = [
            literal("switchport"),
            literal("trunk", "Trunk parameters"),
            literal("allowed", "Allowed VLANs"),
            literal("vlan", "Set allowed VLANs"),
        ]
        add(Mode.INTERFACE, [*trunk_allowed, literal("all", "All VLANs")], self._trunk_all)
        add(Mode.INTERFACE, [*trunk_allowed, literal("none", "No VLANs")], self._trunk_none)
        add(Mode.INTERFACE, [*trunk_allowed, literal("add", "Add VLANs"), argument("vlans", "VLAN list", parse_vlan_list)], self._trunk_add)
        add(Mode.INTERFACE, [*trunk_allowed, literal("remove", "Remove VLANs"), argument("vlans", "VLAN list", parse_vlan_list)], self._trunk_remove)
        add(Mode.INTERFACE, [*trunk_allowed, literal("except", "All except VLANs"), argument("vlans", "VLAN list", parse_vlan_list)], self._trunk_except)
        add(Mode.INTERFACE, [*trunk_allowed, argument("vlans", "VLAN list (for example 5,10-12)", parse_vlan_list)], self._trunk_allowed)
        add(
            Mode.INTERFACE,
            [literal("no", "Negate a command"), *trunk_allowed],
            self._trunk_all,
        )
        trunk_native = [literal("switchport"), literal("trunk"), literal("native", "Native VLAN"), literal("vlan", "Set native VLAN")]
        add(Mode.INTERFACE, [*trunk_native, argument("vlan", "VLAN ID (1-4094)", parse_vlan)], self._trunk_native)
        add(Mode.INTERFACE, [literal("no"), *trunk_native], self._default_trunk_native)

        for mode in (Mode.CONFIG, Mode.VLAN, Mode.INTERFACE):
            add(mode, [literal("end", "Exit to Privileged EXEC")], self._end)
            add(mode, [literal("exit", "Exit from current mode")], self._exit)
        return trees

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
            completed = f"{prefix} {matches[0]}".lstrip() + " "
            return completed, matches
        return line, matches

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
        name = str(values["interface"])
        self.mode, self.context = Mode.INTERFACE, name
        return ""

    def _description(self, values: dict) -> str:
        self.device.interfaces[str(self.context)].description = str(values["description"])
        return ""

    def _no_description(self, _: dict) -> str:
        self.device.interfaces[str(self.context)].description = ""
        return ""

    def _shutdown(self, _: dict) -> str:
        self.device.interfaces[str(self.context)].admin_up = False
        return ""

    def _no_shutdown(self, _: dict) -> str:
        self.device.interfaces[str(self.context)].admin_up = True
        return ""

    def _access_mode(self, _: dict) -> str:
        self.device.interfaces[str(self.context)].switchport_mode = "access"
        return ""

    def _trunk_mode(self, _: dict) -> str:
        self.device.interfaces[str(self.context)].switchport_mode = "trunk"
        return ""

    def _default_switchport_mode(self, _: dict) -> str:
        self.device.interfaces[str(self.context)].switchport_mode = "access"
        return ""

    def _trunk_all(self, _: dict) -> str:
        self.device.interfaces[str(self.context)].allowed_vlans = None
        return ""

    def _trunk_none(self, _: dict) -> str:
        self.device.interfaces[str(self.context)].allowed_vlans = set()
        return ""

    def _trunk_add(self, values: dict) -> str:
        interface = self.device.interfaces[str(self.context)]
        if interface.allowed_vlans is not None:
            interface.allowed_vlans.update(values["vlans"])
        return ""

    def _trunk_remove(self, values: dict) -> str:
        interface = self.device.interfaces[str(self.context)]
        current = set(range(1, 4095)) if interface.allowed_vlans is None else set(interface.allowed_vlans)
        interface.allowed_vlans = current - set(values["vlans"])
        return ""

    def _trunk_except(self, values: dict) -> str:
        self.device.interfaces[str(self.context)].allowed_vlans = set(range(1, 4095)) - set(values["vlans"])
        return ""

    def _trunk_allowed(self, values: dict) -> str:
        self.device.interfaces[str(self.context)].allowed_vlans = set(values["vlans"])
        return ""

    def _access_vlan(self, values: dict) -> str:
        vlan_id = int(values["vlan"])
        self.device.interfaces[str(self.context)].access_vlan = vlan_id
        return ""

    def _default_access_vlan(self, _: dict) -> str:
        self.device.interfaces[str(self.context)].access_vlan = 1
        return ""

    def _trunk_native(self, values: dict) -> str:
        self.device.interfaces[str(self.context)].native_vlan = int(values["vlan"])
        return ""

    def _default_trunk_native(self, _: dict) -> str:
        self.device.interfaces[str(self.context)].native_vlan = 1
        return ""

    def _end(self, _: dict) -> str:
        self.mode, self.context = Mode.PRIVILEGED, None
        return ""

    def _exit(self, _: dict) -> str:
        if self.mode in (Mode.VLAN, Mode.INTERFACE):
            self.mode, self.context = Mode.CONFIG, None
        else:
            self.mode = Mode.PRIVILEGED
        return ""

    def _show_vlan(self, _: dict) -> str:
        vlan_id = _.get("vlan")
        if vlan_id is not None and int(vlan_id) not in self.device.vlans:
            return f"% VLAN {vlan_id} not found"
        return show_vlan(self.device, int(vlan_id) if vlan_id is not None else None)

    def _show_running(self, _: dict) -> str:
        return running_config(self.device)

    def _show_switchport(self, values: dict) -> str:
        return show_switchport(self.device.interfaces[str(values["interface"])])

    def _show_interfaces_trunk(self, values: dict) -> str:
        name = values.get("interface")
        return show_interfaces_trunk(self.device, str(name) if name else None)

    def _show_interfaces_status(self, values: dict) -> str:
        name = values.get("interface")
        return show_interfaces_status(self.device, str(name) if name else None)

    def _show_interfaces_vlans(self, values: dict) -> str:
        name = values.get("interface")
        return show_interfaces_vlans(self.device, str(name) if name else None)

    def _save(self, _: dict) -> str:
        self.device.save_startup()
        return "Copy completed successfully."
