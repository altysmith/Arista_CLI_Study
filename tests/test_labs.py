import unittest

from arista_sim import DeviceState
from arista_sim.labs import get_lab, grade_lab, load_labs, public_lab
from arista_sim.models.device import AccessList, OspfProcess, PolicyClass, StaticRoute


class LabTests(unittest.TestCase):
    def test_catalog_loads_public_lab_without_private_checks(self):
        labs = load_labs()
        self.assertEqual(labs[0]["id"], "access-vlan-basics")
        self.assertTrue({"access-vlan-basics", "trunk-add-vlan", "campus-access-ticket", "campus-trunk-ticket"}.issubset({lab["id"] for lab in labs}))
        self.assertNotIn("checks", public_lab(labs[0]))
        trunk = get_lab("trunk-add-vlan")
        self.assertNotIn("setup_commands", public_lab(trunk))

    def test_access_vlan_lab_grades_device_state(self):
        device = DeviceState()
        lab = get_lab("access-vlan-basics")
        initial = grade_lab(device, lab)
        self.assertFalse(initial["passed"])
        self.assertEqual(initial["passed_count"], 2)

        device.ensure_vlan(20).name = "USERS"
        interface = device.interfaces["Ethernet1"]
        interface.switchport_mode = "access"
        interface.access_vlan = 20
        interface.admin_up = True

        completed = grade_lab(device, lab)
        self.assertTrue(completed["passed"])
        self.assertEqual(completed["passed_count"], completed["total_count"])

    def test_interface_set_attribute_requires_exact_membership(self):
        device = DeviceState()
        interface = device.interfaces["Ethernet48"]
        interface.switchport_mode = "trunk"
        interface.allowed_vlans = {10, 20}
        lab = get_lab("trunk-add-vlan")

        self.assertFalse(grade_lab(device, lab)["passed"])
        interface.allowed_vlans.add(30)
        self.assertTrue(grade_lab(device, lab)["passed"])
        interface.allowed_vlans.remove(10)
        self.assertFalse(grade_lab(device, lab)["passed"])

    def test_unknown_lab_is_rejected(self):
        with self.assertRaises(KeyError):
            get_lab("missing")

    def test_static_default_route_lab_grades_local_route_state(self):
        device = DeviceState()
        lab = get_lab("static-default-route")
        self.assertFalse(grade_lab(device, lab)["passed"])
        device.ip_routing = True
        device.static_routes.append(StaticRoute("0.0.0.0/0", "192.0.2.1"))
        grade = grade_lab(device, lab, ["show ip route"])
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["process_passed_count"], 1)

    def test_ospf_local_basics_grades_local_process_state(self):
        device = DeviceState()
        lab = get_lab("ospf-local-basics")
        self.assertFalse(grade_lab(device, lab)["passed"])

        device.ospf_processes[100] = OspfProcess(
            100,
            router_id="10.255.0.1",
            networks=[("10.0.0.0/8", "0.0.0.0")],
        )
        grade = grade_lab(device, lab, ["show ip ospf"])
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["process_passed_count"], 1)

    def test_acl_management_edge_grades_order_and_inbound_binding(self):
        device = DeviceState()
        lab = get_lab("acl-management-edge")
        self.assertFalse(grade_lab(device, lab)["passed"])

        device.access_lists["MGMT-SAFE"] = AccessList("MGMT-SAFE", [
            "10 permit tcp 192.0.2.0/24 any eq ssh",
            "20 deny ip any any",
        ])
        device.interfaces["Ethernet1"].ip_access_groups["in"] = "MGMT-SAFE"
        grade = grade_lab(device, lab, ["show ip access-lists MGMT-SAFE", "show running-config"])
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["process_passed_count"], 2)

    def test_dhcp_snooping_trust_grades_protected_vlan_and_uplink(self):
        device = DeviceState()
        lab = get_lab("dhcp-snooping-trust")
        self.assertFalse(grade_lab(device, lab)["passed"])

        device.dhcp_snooping_enabled = True
        device.dhcp_snooping_vlans.add(20)
        device.interfaces["Ethernet48"].dhcp_snooping_trust = True
        grade = grade_lab(device, lab, ["show ip dhcp snooping", "show running-config"])
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["process_passed_count"], 2)

    def test_qos_voice_marking_grades_classification_marking_and_attachment(self):
        device = DeviceState()
        lab = get_lab("qos-voice-marking")
        self.assertFalse(grade_lab(device, lab)["passed"])

        device.access_lists["VOICE-ACL"] = AccessList("VOICE-ACL", ["10 permit udp any any"])
        device.ensure_class_map("VOICE").access_group = "VOICE-ACL"
        device.ensure_policy_map("EDGE-QOS").classes["VOICE"] = PolicyClass("VOICE", ["set dscp 46"])
        device.interfaces["Ethernet1"].service_policies["input"] = "EDGE-QOS"
        grade = grade_lab(device, lab, ["show policy-map", "show running-config"])
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["process_passed_count"], 2)

    def test_branch_routing_readiness_grades_local_route_and_ospf_state(self):
        device = DeviceState()
        lab = get_lab("branch-routing-readiness")
        self.assertFalse(grade_lab(device, lab)["passed"])

        device.ip_routing = True
        device.static_routes.append(StaticRoute("0.0.0.0/0", "192.0.2.1"))
        device.ospf_processes[100] = OspfProcess(
            100,
            router_id="10.255.0.1",
            networks=[("10.0.0.0/8", "0.0.0.0")],
        )
        grade = grade_lab(device, lab, ["show ip route", "show ip ospf", "show ip ospf neighbor"])
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["process_passed_count"], 3)

    def test_qos_policy_not_applied_requires_edge_attachment(self):
        device = DeviceState()
        lab = get_lab("qos-policy-not-applied")
        device.access_lists["VOICE-ACL"] = AccessList("VOICE-ACL", ["10 permit udp any any"])
        device.ensure_class_map("VOICE").access_group = "VOICE-ACL"
        device.ensure_policy_map("EDGE-QOS").classes["VOICE"] = PolicyClass("VOICE", ["set dscp 46"])
        self.assertFalse(grade_lab(device, lab)["passed"])

        device.interfaces["Ethernet1"].service_policies["input"] = "EDGE-QOS"
        grade = grade_lab(device, lab, ["show policy-map", "show running-config"])
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["process_passed_count"], 2)

    def test_dhcp_snooping_trust_repair_moves_trust_to_the_uplink(self):
        device = DeviceState()
        lab = get_lab("dhcp-snooping-trust-repair")
        device.dhcp_snooping_enabled = True
        device.dhcp_snooping_vlans.add(20)
        device.interfaces["Ethernet1"].dhcp_snooping_trust = True
        self.assertFalse(grade_lab(device, lab)["passed"])

        device.interfaces["Ethernet1"].dhcp_snooping_trust = False
        device.interfaces["Ethernet48"].dhcp_snooping_trust = True
        grade = grade_lab(device, lab, ["show ip dhcp snooping", "show running-config"])
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["process_passed_count"], 2)

    def test_acl_wrong_direction_requires_inbound_only_attachment(self):
        device = DeviceState()
        lab = get_lab("acl-wrong-direction")
        device.access_lists["MGMT-SAFE"] = AccessList("MGMT-SAFE", ["10 permit tcp 192.0.2.0/24 any eq ssh", "20 deny ip any any"])
        device.interfaces["Ethernet1"].ip_access_groups["out"] = "MGMT-SAFE"
        self.assertFalse(grade_lab(device, lab)["passed"])

        device.interfaces["Ethernet1"].ip_access_groups = {"in": "MGMT-SAFE"}
        grade = grade_lab(device, lab, ["show ip access-lists MGMT-SAFE", "show running-config"])
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["process_passed_count"], 2)

    def test_ospf_no_neighbor_diagnosis_requires_evidence_checks(self):
        device = DeviceState()
        lab = get_lab("ospf-no-neighbor-diagnosis")
        device.ospf_processes[100] = OspfProcess(100, router_id="10.255.0.1", networks=[("10.0.0.0/8", "0.0.0.0")])
        self.assertFalse(grade_lab(device, lab)["passed"])
        grade = grade_lab(device, lab, ["show ip ospf", "show ip ospf interface brief", "show ip ospf neighbor"])
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["process_passed_count"], 3)

    def test_mlag_peer_link_repair_requires_local_peer_link(self):
        device = DeviceState()
        lab = get_lab("mlag-peer-link-repair")
        device.mlag.domain_id = "CAMPUS"
        device.mlag.local_interface = "Vlan4094"
        device.mlag.peer_address = "10.255.255.2"
        self.assertFalse(grade_lab(device, lab)["passed"])

        device.mlag.peer_link = "Port-Channel100"
        grade = grade_lab(device, lab, ["show mlag", "show running-config"])
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["process_passed_count"], 2)


if __name__ == "__main__":
    unittest.main()
