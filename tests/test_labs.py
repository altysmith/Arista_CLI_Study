import unittest

from arista_sim import DeviceState
from arista_sim.labs import get_lab, grade_lab, load_labs, public_lab


class LabTests(unittest.TestCase):
    def test_catalog_loads_public_lab_without_private_checks(self):
        labs = load_labs()
        self.assertEqual(labs[0]["id"], "access-vlan-basics")
        self.assertEqual({lab["id"] for lab in labs}, {"access-vlan-basics", "trunk-add-vlan"})
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


if __name__ == "__main__":
    unittest.main()
