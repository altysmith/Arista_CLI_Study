from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from .models.device import DeviceState


def load_labs() -> list[dict[str, Any]]:
    lab_directory = files("arista_sim").joinpath("labs")
    labs = []
    for resource in sorted(lab_directory.iterdir(), key=lambda item: item.name):
        if resource.name.endswith(".json"):
            labs.append(json.loads(resource.read_text(encoding="utf-8")))
    return labs


def load_sections() -> list[dict[str, Any]]:
    resource = files("arista_sim").joinpath("reference", "sections.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def get_lab(lab_id: str) -> dict[str, Any]:
    for lab in load_labs():
        if lab["id"] == lab_id:
            return lab
    raise KeyError(lab_id)


def public_lab(lab: dict[str, Any]) -> dict[str, Any]:
    private_keys = {"checks", "setup_commands", "campus_fault", "process_checks"}
    return {key: value for key, value in lab.items() if key not in private_keys}


def grade_lab(device: DeviceState, lab: dict[str, Any], history: list[str] | None = None) -> dict[str, Any]:
    results = [_grade_check(device, check) for check in lab["checks"]]
    passed_count = sum(result["passed"] for result in results)
    grade = {
        "passed": passed_count == len(results),
        "passed_count": passed_count,
        "total_count": len(results),
        "results": results,
    }
    checks = lab.get("process_checks", [])
    if checks:
        commands = [command.casefold() for command in history or []]
        process = [{"label": check["label"], "passed": any(command.startswith(check["command"].casefold()) for command in commands)} for check in checks]
        grade.update({"process": process, "process_passed_count": sum(item["passed"] for item in process), "process_total_count": len(process)})
    return grade


def _grade_check(device: DeviceState, check: dict[str, Any]) -> dict[str, Any]:
    check_type = check["type"]
    passed = False

    if check_type == "vlan_exists":
        passed = int(check["vlan"]) in device.vlans
    elif check_type == "device_attribute":
        attribute = str(check["attribute"])
        passed = attribute in device.__dataclass_fields__ and getattr(device, attribute) == check["equals"]
    elif check_type == "vlan_name":
        vlan = device.vlans.get(int(check["vlan"]))
        passed = vlan is not None and vlan.name == check["equals"]
    elif check_type == "mlag_attribute":
        attribute = str(check["attribute"])
        passed = (
            attribute in device.mlag.__dataclass_fields__
            and getattr(device.mlag, attribute) == check["equals"]
        )
    elif check_type == "interface_attribute":
        interface = device.interfaces.get(str(check["interface"]))
        attribute = str(check["attribute"])
        expected = check["equals"]
        actual = getattr(interface, attribute) if interface is not None and attribute in interface.__dataclass_fields__ else None
        if isinstance(actual, set) and isinstance(expected, list):
            expected = set(expected)
        passed = (
            interface is not None
            and attribute in interface.__dataclass_fields__
            and actual == expected
        )
    elif check_type == "static_route":
        passed = any(route.prefix == check["prefix"] and route.next_hop == check["next_hop"] for route in device.static_routes)
    elif check_type == "ospf_process":
        process = device.ospf_processes.get(int(check["process_id"]))
        passed = process is not None and process.router_id == check["router_id"] and (check["network"], check["area"]) in process.networks
    else:
        raise ValueError(f"Unsupported lab check type: {check_type}")

    return {"label": check["label"], "passed": passed}
