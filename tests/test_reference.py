import unittest

from arista_sim.reference import load_command_reference


class CommandReferenceTests(unittest.TestCase):
    def test_reference_has_unique_categories_and_commands(self):
        reference = load_command_reference()
        categories = reference["categories"]
        category_ids = [category["id"] for category in categories]
        commands = [
            item["command"]
            for category in categories
            for item in category["commands"]
        ]

        self.assertEqual(len(category_ids), len(set(category_ids)))
        self.assertEqual(len(commands), len(set(commands)))
        self.assertIn("show interfaces trunk", commands)
        self.assertIn("switchport trunk allowed vlan add <LIST>", commands)
        self.assertIn("show mlag", commands)

    def test_every_reference_item_has_a_description(self):
        reference = load_command_reference()
        for category in reference["categories"]:
            self.assertTrue(category["title"])
            for item in category["commands"]:
                self.assertTrue(item["command"])
                self.assertTrue(item["description"])


if __name__ == "__main__":
    unittest.main()
