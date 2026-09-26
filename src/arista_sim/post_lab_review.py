from __future__ import annotations

from typing import Any


_REVIEWS = {
    "acl-wrong-direction": ("SSH policy behavior is wrong even though MGMT-SAFE has the approved rules.", "MGMT-SAFE was attached outbound on Ethernet1 instead of inbound.", "Do not recreate a correct ACL or add broader permits before checking its interface binding direction.", ["show ip access-lists MGMT-SAFE", "show running-config", "Correct only the attachment direction", "Verify the inbound binding"]),
    "campus-access-ticket": ("STAFF-A cannot reach STAFF-B while student traffic must remain available.", "The affected staff access-port state is wrong in the campus topology.", "Do not change trunks or remove VLANs before host tests and port evidence isolate the access edge.", ["Test the affected and preserved host paths", "Inspect LLDP, MAC learning, and the access port", "Repair the single access-port fault", "Re-test staff and student paths"]),
    "campus-trunk-ticket": ("Students cannot communicate between Colleges A and B while staff connectivity still works.", "VLAN 20 is absent from the affected uplink trunk allowance.", "Do not replace the whole allowed-VLAN list; that can interrupt staff VLAN 10 or management VLAN 99.", ["Confirm the asymmetric host symptom", "Inspect the inter-switch trunk and MAC evidence", "Add only VLAN 20 to the affected trunk", "Re-test student and preserved traffic"]),
    "dhcp-snooping-trust-repair": ("VLAN 20 clients cannot obtain valid DHCP leases after source-validation rollout.", "Endpoint-facing Ethernet1 was trusted instead of infrastructure-facing Ethernet48.", "Do not disable DHCP snooping to restore service; retain protection and move trust to the legitimate uplink.", ["show ip dhcp snooping", "show running-config", "Remove trust from Ethernet1", "Trust Ethernet48 and verify the boundary"]),
    "mlag-peer-link-repair": ("The local MLAG configuration has a domain and peer address but lacks a peer link.", "Port-Channel100 was not configured as the local MLAG peer link.", "Do not claim peer health or rebuild the domain; this simulator verifies local configuration only.", ["show mlag", "show running-config", "Configure Port-Channel100 as peer link", "Re-check local MLAG state"]),
    "qos-policy-not-applied": ("Voice classification and marking exist, but expected edge behavior does not take effect.", "EDGE-QOS was not attached input on Ethernet1.", "Do not rebuild the ACL, class map, or policy before confirming whether the existing policy is attached.", ["show policy-map", "show running-config", "Attach EDGE-QOS input on Ethernet1", "Verify the interface attachment"]),
    "routed-static-next-hop-ticket": ("The branch route points toward an unreachable next hop.", "The configured static route uses the wrong next-hop address.", "Do not add competing routes before checking the route entry and connected uplink network.", ["show ip route", "Inspect the connected uplink", "Correct the route next hop", "Verify the selected route"]),
    "routed-static-return-ticket": ("Forward routing exists, but reply traffic has no path back to the source network.", "The required return route is missing.", "Do not change OSPF or default routes when the evidence points to a specific missing return prefix.", ["show ip route", "Identify the missing return prefix", "Add the smallest static return route", "Verify route selection"]),
    "ospf-area-mismatch-ticket": ("The routed campus has OSPF configuration but adjacency cannot form across the link.", "The peers use different OSPF area values on the shared network.", "Do not change router IDs or add networks until interface and neighbor evidence identifies the area mismatch.", ["show ip ospf interface brief", "show ip ospf neighbor", "Align the shared-link area", "Verify adjacency and route evidence"]),
    "ospf-link-down-ticket": ("The OSPF adjacency is absent because the routed inter-switch link is down.", "The relevant routed interface is administratively disabled.", "Do not change OSPF process settings before proving the underlying link is up.", ["show interfaces status", "show ip ospf interface brief", "Enable the affected routed interface", "Verify neighbor and route state"]),
    "ospf-missing-advertisement-ticket": ("A remote LAN is missing from the learned OSPF routes.", "The site LAN is not advertised by the relevant OSPF process.", "Do not add a static route as a workaround before checking the originating router's OSPF networks.", ["show ip route", "show ip ospf", "Add the missing network advertisement", "Verify the learned prefix"]),
    "ospf-prefix-selection-ticket": ("Traffic selects an unexpected route when both a summary and a more-specific prefix are present.", "The routing table correctly prefers the longest matching OSPF prefix.", "Do not alter administrative distance to override normal longest-prefix selection.", ["show ip route", "Compare matching prefix lengths", "Confirm the longest-prefix decision", "Document the selected next hop"]),
    "ospf-route-source-ticket": ("The route table contains both static and OSPF information for the destination.", "The static route wins because its administrative distance is lower than OSPF's.", "Do not delete OSPF configuration merely because the static route is selected.", ["show ip route", "Compare prefix and administrative distance", "Identify the selected source", "Verify forwarding policy"]),
    "ospf-no-neighbor-diagnosis": ("The local OSPF process is configured, but no neighbor appears.", "This single-device lab has no remote peer topology; an empty neighbor table is expected.", "Do not invent a local repair or claim an adjacency formed without a modeled peer.", ["show ip ospf", "show ip ospf interface brief", "show ip ospf neighbor", "Record the remote-peer boundary"]),
}


def post_lab_review(lab: dict[str, Any]) -> dict[str, Any]:
    """Return post-completion coaching without exposing ticket answers before grading."""
    review = _REVIEWS.get(lab["id"])
    if review:
        symptom, root_cause, avoid, path = review
        return {"symptom": symptom, "root_cause": root_cause, "avoid": avoid, "path": path}
    checks = "; ".join(check["label"] for check in lab["checks"])
    return {
        "symptom": f"This was a build-and-verify exercise for {lab['title']}.",
        "root_cause": f"The required local state was absent or incomplete: {checks}.",
        "avoid": "Do not add unrelated configuration before checking the requested state and its direct verification output.",
        "path": ["Inspect the requested state", "Make the smallest required configuration change", "Run the lab's verification commands", "Confirm the graded state"],
    }
