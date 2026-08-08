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


if __name__ == "__main__":
    unittest.main()
