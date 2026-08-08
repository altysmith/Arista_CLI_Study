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
