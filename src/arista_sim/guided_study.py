"""Guided, lab-gated study sessions built from the existing curriculum."""
from __future__ import annotations

from typing import Any

from .curriculum import load_curriculum
from .exercises import exercise_choices, load_exercise_families, public_exercise


_LESSONS = {
    "ethernet-forwarding": ("Frames stay inside a Layer 2 broadcast domain. Switches learn source MAC addresses, then use that evidence to select an egress port.", "campus-access-ticket"),
    "ipv4-local-delivery": ("Before sending traffic, decide whether the destination is local by applying the prefix. Local traffic ARPs for the destination; remote traffic ARPs for the gateway.", "campus-access-ticket"),
    "dhcp-dns-transport": ("Troubleshoot service symptoms by separating addressing, name resolution, reachability, and transport evidence instead of changing several layers at once.", "dhcp-snooping-trust"),
    "eos-cli-workflow": ("EOS work is mode-aware: inspect before changing state, understand running versus startup configuration, and verify the exact state you changed.", "access-vlan-basics"),
    "eos-interface-workflow": ("Start with the lowest unproven dependency. Interface administrative and operational state are evidence before you assume a VLAN, routing, or application fault.", "access-vlan-basics"),
    "vlan-trunks": ("A VLAN assigns a broadcast domain; a trunk carries selected VLANs between switches. Small allowed-list changes must preserve working VLANs.", "trunk-add-vlan"),
    "stp-lacp-mlag": ("Redundancy depends on distinct roles: STP prevents loops, LACP negotiates bundles, and MLAG coordinates a peer pair and downstream attachment.", "mlag-campus-repair"),
    "route-selection": ("Route selection starts with the longest matching prefix. Administrative distance matters only between routes to the same prefix.", "static-default-route"),
    "ospf-workflow": ("Dynamic routing troubleshooting follows dependencies: link and interface participation, neighbor adjacency, advertisement, then route selection.", "ospf-local-basics"),
    "ipv6-fundamentals": ("IPv6 uses prefixes and neighbor discovery for local delivery. Treat address, prefix, and next-hop evidence as separate checks.", "static-default-route"),
    "acl-workflow": ("ACLs evaluate entries in order. A correct rule list still needs the correct interface and direction to affect the intended traffic.", "acl-management-edge"),
    "access-layer-security": ("DHCP snooping protects client VLANs by trusting only legitimate infrastructure paths while leaving endpoints untrusted.", "dhcp-snooping-trust"),
    "qos-workflow": ("QoS configuration is a chain: classify traffic, define an action, attach the policy, then verify the attachment before claiming behavior.", "qos-voice-marking"),
}


def _topics() -> list[dict[str, Any]]:
    return [topic | {"section": section["title"]} for section in reversed(load_curriculum()["sections"]) for domain in section["domains"] for topic in domain["topics"]]


def guided_catalog(progress: list[dict[str, Any]], completions: dict[str, dict[str, Any]], attempts: dict[str, int]) -> dict[str, Any]:
    families = load_exercise_families()
    entries = []
    for topic in _topics():
        lesson, lab_id = _LESSONS[topic["id"]]
        questions = [public_exercise(family, family["variants"][attempts.get(family["id"], 0) % len(family["variants"])], "Guided study recall") for family in families if family["topic_id"] == topic["id"]]
        entries.append({
            "id": topic["id"], "title": topic["title"], "section": topic["section"], "priority": topic["priority"],
            "lesson": lesson, "lab_id": lab_id, "questions": questions, "completion": completions.get(topic["id"]),
        })
    return {"topics": entries}


def guided_topic(topic_id: str, progress: list[dict[str, Any]], completions: dict[str, dict[str, Any]], attempts: dict[str, int]) -> dict[str, Any]:
    catalog = guided_catalog(progress, completions, attempts)
    for topic in catalog["topics"]:
        if topic["id"] == topic_id:
            return topic
    raise KeyError("Guided topic not found")


def valid_guided_answer(topic_id: str, exercise_id: str, variant_id: str) -> bool:
    family = next((item for item in load_exercise_families() if item["id"] == exercise_id), None)
    return bool(family and family["topic_id"] == topic_id and any(item["id"] == variant_id for item in family["variants"]))
