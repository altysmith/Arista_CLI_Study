import unittest

from arista_sim import Session
from arista_sim.cli.session import Mode


class CliTests(unittest.TestCase):
    def setUp(self):
        self.session = Session()

    def enter_config(self):
        self.session.execute("enable")
        self.session.execute("configure")

    def test_modes_and_hostname_change_prompt(self):
        self.assertEqual(self.session.prompt, "switch>")
        self.assertEqual(self.session.execute("configure"), "% Invalid input")
        self.session.execute("en")
        self.assertEqual(self.session.prompt, "switch#")
        self.session.execute("conf")
        self.session.execute("hostname SW1")
        self.assertEqual(self.session.prompt, "SW1(config)#")
        self.session.execute("end")
        self.session.execute("dis")
        self.assertEqual(self.session.prompt, "SW1>")

    def test_documented_ambiguity(self):
        self.session.execute("enable")
        self.assertEqual(self.session.execute("con"), "% Ambiguous command")
        self.assertEqual(self.session.mode, Mode.PRIVILEGED)

    def test_contextual_help(self):
        self.assertIn("enable", self.session.execute("?"))
        self.session.execute("enable")
        self.assertIn("running-config", self.session.execute("show ?"))
        self.session.execute("configure")
        self.assertIn("<interface>", self.session.execute("interface ?"))
        self.session.execute("int et1")
        self.assertIn("mode", self.session.execute("switchport ?"))

    def test_completion(self):
        self.session.execute("enable")
        completed, matches = self.session.complete("conf")
        self.assertEqual(completed, "configure ")
        self.assertEqual(matches, ["configure"])
        unchanged, matches = self.session.complete("con")
        self.assertEqual(unchanged, "con")
        self.assertEqual(matches, ["configure", "connect"])

    def test_vlan_and_interface_reference_transcript(self):
        self.enter_config()
        commands = [
            "hostname SW1",
            "vlan 20",
            "name STUDENTS",
            "exit",
            "interface ethernet 1",
            "description Student-PC",
            "switchport mode access",
            "switchport access vlan 20",
            "no shutdown",
            "end",
        ]
        for command in commands:
            self.assertEqual(self.session.execute(command), "", command)
        vlan_output = self.session.execute("show vlan")
        self.assertIn("20    STUDENTS", vlan_output)
        self.assertIn("Et1", vlan_output)
        switchport = self.session.execute("show interfaces ethernet 1 switchport")
        self.assertIn("Administrative Mode: access", switchport)
        self.assertIn("Access Mode VLAN: 20", switchport)
        config = self.session.execute("show running-config")
        self.assertIn("hostname SW1", config)
        self.assertIn("vlan 20\n   name STUDENTS", config)
        self.assertIn("interface Ethernet1", config)

    def test_compact_interface_abbreviation(self):
        self.enter_config()
        self.assertEqual(self.session.execute("int et1"), "")
        self.assertEqual(self.session.prompt, "switch(config-if-Et1)#")

    def test_description_accepts_remaining_text(self):
        self.enter_config()
        self.session.execute("interface et1")
        self.assertEqual(self.session.execute("description Student access port"), "")
        self.assertEqual(self.session.device.interfaces["Ethernet1"].description, "Student access port")

    def test_trunk_help_and_allowed_vlan_list(self):
        self.enter_config()
        self.session.execute("interface et48")
        trunk_help = self.session.execute("switchport trunk ?")
        self.assertIn("allowed", trunk_help)
        self.assertIn("native", trunk_help)
        self.assertIn("vlan", self.session.execute("switchport trunk allowed ?"))
        final_help = self.session.execute("switchport trunk allowed vlan ?")
        self.assertIn("all", final_help)
        self.assertIn("none", final_help)
        self.assertIn("add", final_help)
        self.assertIn("remove", final_help)
        self.assertIn("except", final_help)
        self.assertIn("<vlans>", final_help)
        self.assertEqual(self.session.execute("switchport mode trunk"), "")
        self.assertEqual(self.session.execute("switchport trunk allowed vlan 5,10-12"), "")
        interface = self.session.device.interfaces["Ethernet48"]
        self.assertEqual(interface.allowed_vlans, {5, 10, 11, 12})
        self.session.execute("end")
        output = self.session.execute("show interfaces et48 switchport")
        self.assertIn("Trunking VLANs Enabled: 5,10-12", output)

    def test_show_interfaces_trunk_and_native_vlan(self):
        self.enter_config()
        for command in (
            "vlan 5",
            "exit",
            "vlan 10",
            "exit",
            "interface et48",
            "switchport mode trunk",
            "switchport trunk native vlan 5",
            "switchport trunk allowed vlan 5,10-12",
            "end",
        ):
            self.assertEqual(self.session.execute(command), "", command)
        output = self.session.execute("show interfaces trunk")
        self.assertIn("Et48", output)
        self.assertIn("trunking", output)
        self.assertIn("5,10-12", output)
        self.assertIn("Vlans allowed and active", output)
        self.assertIn("5,10", output)
        filtered = self.session.execute("show int et48 trunk")
        self.assertIn("Native vlan", filtered)
        self.assertIn("Et48", filtered)

    def test_layer2_verification_is_available_in_exec_mode(self):
        self.assertIn("status", self.session.execute("show interfaces ?"))
        self.assertIn("Port", self.session.execute("show interfaces status"))
        self.assertEqual(self.session.execute("show interfaces trunk"), "No trunk interfaces configured")

    def test_trunk_allowed_edit_actions_and_resets(self):
        self.enter_config()
        self.session.execute("interface et48")
        self.session.execute("switchport trunk allowed vlan none")
        self.session.execute("switchport trunk allowed vlan add 5,10-12")
        self.session.execute("switchport trunk allowed vlan remove 11")
        self.assertEqual(self.session.device.interfaces["Ethernet48"].allowed_vlans, {5, 10, 12})
        self.session.execute("switchport trunk allowed vlan except 1-4093")
        self.assertEqual(self.session.device.interfaces["Ethernet48"].allowed_vlans, {4094})
        self.session.execute("no switchport trunk allowed vlan")
        self.assertIsNone(self.session.device.interfaces["Ethernet48"].allowed_vlans)
        self.session.execute("switchport trunk native vlan 20")
        self.session.execute("no switchport trunk native vlan")
        self.assertEqual(self.session.device.interfaces["Ethernet48"].native_vlan, 1)

    def test_interface_status_and_vlan_membership_views(self):
        self.enter_config()
        self.session.execute("interface et1")
        self.session.execute("description Student Port")
        self.session.execute("switchport access vlan 20")
        self.session.execute("shutdown")
        self.session.execute("end")
        status = self.session.execute("show interfaces et1 status")
        self.assertIn("Student Port", status)
        self.assertIn("disabled", status)
        self.assertIn("20", status)
        vlans = self.session.execute("show interfaces et1 vlans")
        self.assertIn("Et1", vlans)
        self.assertIn("20", vlans)

    def test_no_forms_restore_defaults_and_remove_vlan(self):
        self.enter_config()
        self.session.execute("vlan 20")
        self.session.execute("name STUDENTS")
        self.session.execute("no name")
        self.assertEqual(self.session.device.vlans[20].name, "")
        self.session.execute("exit")
        self.session.execute("interface et1")
        self.session.execute("description Temporary")
        self.session.execute("switchport access vlan 20")
        self.session.execute("switchport mode trunk")
        self.session.execute("no description")
        self.session.execute("no switchport access vlan")
        self.session.execute("no switchport mode")
        interface = self.session.device.interfaces["Ethernet1"]
        self.assertEqual(interface.description, "")
        self.assertEqual(interface.access_vlan, 1)
        self.assertEqual(interface.switchport_mode, "access")
        self.session.execute("exit")
        self.session.execute("no vlan 20")
        self.assertNotIn(20, self.session.device.vlans)
        self.assertEqual(self.session.execute("no vlan 1"), "% VLAN 1 cannot be removed")

    def test_show_single_vlan_and_missing_vlan(self):
        self.enter_config()
        self.session.execute("vlan 20")
        self.session.execute("name STUDENTS")
        self.session.execute("end")
        output = self.session.execute("show vlan 20")
        self.assertIn("STUDENTS", output)
        self.assertNotIn("default", output)
        self.assertEqual(self.session.execute("show vlan 999"), "% VLAN 999 not found")

    def test_command_execution_records_history(self):
        self.session.execute("enable")
        self.session.execute("show vlan")
        self.assertEqual(self.session.history, ["enable", "show vlan"])

    def test_invalid_and_incomplete_do_not_mutate(self):
        self.enter_config()
        self.assertEqual(self.session.execute("vlan"), "% Incomplete command")
        self.assertEqual(self.session.execute("vlan 5000"), "% Invalid input")
        self.assertNotIn(5000, self.session.device.vlans)
        self.assertEqual(self.session.execute("interface Ethernet99"), "% Invalid input")

    def test_running_and_startup_are_separate(self):
        self.enter_config()
        self.session.execute("hostname SAVED")
        self.session.execute("end")
        self.assertEqual(self.session.execute("copy running-config startup-config"), "Copy completed successfully.")
        self.session.execute("configure")
        self.session.execute("hostname CHANGED")
        self.assertEqual(self.session.device.startup.hostname, "SAVED")
        self.assertEqual(self.session.device.hostname, "CHANGED")

    def test_exit_moves_up_one_level_and_end_moves_to_privileged(self):
        self.enter_config()
        self.session.execute("vlan 20")
        self.session.execute("exit")
        self.assertEqual(self.session.mode, Mode.CONFIG)
        self.session.execute("interface et1")
        self.session.execute("end")
        self.assertEqual(self.session.mode, Mode.PRIVILEGED)

    def test_management_svi_and_static_routing_workflow(self):
        self.enter_config()
        commands = (
            "interface management 1",
            "ip address 192.0.2.2/24",
            "exit",
            "ip routing",
            "interface vlan 10",
            "ip address 10.0.10.1/24",
            "exit",
            "ip route 0.0.0.0/0 192.0.2.1",
            "end",
        )
        for command in commands:
            self.assertEqual(self.session.execute(command), "", command)
        brief = self.session.execute("show ip interface brief")
        self.assertIn("Ma1", brief)
        self.assertIn("10.0.10.1/24", brief)
        routes = self.session.execute("show ip route")
        self.assertIn("10.0.10.0/24", routes)
        self.assertIn("0.0.0.0/0 via 192.0.2.1", routes)

    def test_router_on_a_stick_subinterface(self):
        self.enter_config()
        for command in (
            "interface et1.20",
            "encapsulation dot1q vlan 20",
            "ip address 10.20.0.1/24",
            "end",
        ):
            self.assertEqual(self.session.execute(command), "", command)
        config = self.session.execute("show running-config")
        self.assertIn("interface Ethernet1.20", config)
        self.assertIn("encapsulation dot1q vlan 20", config)
        self.assertIn("ip address 10.20.0.1/24", config)

    def test_interface_range_lacp_and_mlag_workflow(self):
        self.enter_config()
        commands = (
            "interface ethernet 1-2",
            "channel-group 10 mode active",
            "exit",
            "interface port-channel 10",
            "switchport mode trunk",
            "mlag 10",
            "exit",
            "mlag configuration",
            "domain-id LAB",
            "local-interface vlan 4094",
            "peer-address 10.0.0.2",
            "peer-link port-channel 10",
            "end",
        )
        for command in commands:
            self.assertEqual(self.session.execute(command), "", command)
        port_channel = self.session.execute("show port-channel dense")
        self.assertIn("Po10(U)", port_channel)
        self.assertIn("Et1(P+)", port_channel)
        mlag = self.session.execute("show mlag")
        self.assertIn("domain-id         : LAB", mlag)
        self.assertIn("Configured (no peer topology)", mlag)

    def test_spanning_tree_configuration_and_show(self):
        self.enter_config()
        self.session.execute("spanning-tree mode rapid-pvst")
        self.session.execute("spanning-tree vlan 10 priority 24576")
        self.session.execute("interface et1")
        self.session.execute("spanning-tree portfast edge")
        self.session.execute("spanning-tree port-priority 64")
        self.session.execute("end")
        output = self.session.execute("show spanning-tree")
        self.assertIn("rapid-pvst", output)
        config = self.session.execute("show running-config")
        self.assertIn("spanning-tree vlan 10 priority 24576", config)
        self.assertIn("spanning-tree portfast edge", config)

    def test_rip_configuration_and_verification(self):
        self.enter_config()
        self.assertEqual(self.session.execute("router rip"), "")
        self.assertEqual(self.session.prompt, "switch(config-router-rip)#")
        self.session.execute("network 10.0.0.0/8")
        self.session.execute("redistribute static")
        self.session.execute("end")
        protocols = self.session.execute("show ip protocols")
        self.assertIn("Routing Protocol is 'rip'", protocols)
        self.assertIn("10.0.0.0/8", protocols)

    def test_ospf_configuration_and_verification(self):
        self.enter_config()
        for command in (
            "router ospf 100",
            "router-id 10.255.0.1",
            "network 10.0.0.0/8 area 0",
            "redistribute static",
            "end",
        ):
            self.assertEqual(self.session.execute(command), "", command)
        self.assertIn("OSPF Routing Process 100", self.session.execute("show ip ospf"))
        self.assertIn("No OSPF neighbors", self.session.execute("show ip ospf neighbor"))
        self.assertIn("10.0.0.0/8", self.session.execute("show ip ospf interface brief"))
        config = self.session.execute("show running-config")
        self.assertIn("router ospf 100", config)
        self.assertIn("network 10.0.0.0/8 area 0.0.0.0", config)

    def test_acl_interface_control_plane_and_service_workflow(self):
        self.enter_config()
        for command in (
            "ip access-list MGMT",
            "10 permit tcp 192.0.2.0/24 any eq ssh",
            "20 deny ip any any",
            "exit",
            "interface et1",
            "ip access-group MGMT in",
            "exit",
            "control-plane",
            "ip access-group MGMT in",
            "exit",
            "management ssh",
            "ip access-group MGMT in",
            "end",
        ):
            self.assertEqual(self.session.execute(command), "", command)
        output = self.session.execute("show ip access-lists MGMT")
        self.assertIn("10 permit tcp", output)
        self.assertIn("20 deny ip any any", output)
        self.assertIn("MGMT", self.session.execute("show management ssh ip access-list"))

    def test_qos_class_policy_and_interface_attachment(self):
        self.enter_config()
        commands = (
            "ip access-list VOICE-ACL",
            "10 permit udp any any",
            "exit",
            "class-map type qos match-any VOICE",
            "match ip access-group VOICE-ACL",
            "exit",
            "policy-map type quality-of-service EDGE-QOS",
            "class VOICE",
            "set dscp 46",
            "police cir 512000 bc 96000",
            "exit",
            "exit",
            "interface et1",
            "service-policy type qos input EDGE-QOS",
            "end",
        )
        for command in commands:
            self.assertEqual(self.session.execute(command), "", command)
        output = self.session.execute("show policy-map")
        self.assertIn("Service-policy EDGE-QOS", output)
        self.assertIn("set dscp 46", output)
        self.assertIn("police cir 512000 bc 96000", output)

    def test_ipv6_addressing_and_static_route(self):
        self.enter_config()
        for command in (
            "ipv6 unicast-routing",
            "interface loopback 0",
            "ipv6 address 2001:db8::1/128",
            "exit",
            "ipv6 route 2001:db8:1::/64 2001:db8::2",
            "end",
        ):
            self.assertEqual(self.session.execute(command), "", command)
        self.assertIn("2001:db8::1/128", self.session.execute("show ipv6 interface brief"))
        self.assertIn("2001:db8:1::/64 via 2001:db8::2", self.session.execute("show ipv6 route"))

    def test_topology_dependent_commands_do_not_fake_results(self):
        self.assertIn("No LLDP neighbors", self.session.execute("show lldp neighbors"))
        self.assertIn("No ARP entries", self.session.execute("show arp"))
        self.assertIn("cannot be determined", self.session.execute("ping 192.0.2.1"))

    def test_new_command_families_are_discoverable(self):
        self.enter_config()
        root_help = self.session.execute("?")
        for keyword in ("class-map", "control-plane", "ip", "ipv6", "mlag", "policy-map", "router", "spanning-tree"):
            self.assertIn(keyword, root_help)
        self.session.execute("interface vlan 10")
        self.assertIn("address", self.session.execute("ip ?"))
        self.assertIn("address", self.session.execute("ipv6 ?"))


if __name__ == "__main__":
    unittest.main()
