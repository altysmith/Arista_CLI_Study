import unittest

from arista_sim.curriculum import SkillMastery, TrainingMode, load_curriculum, validate_curriculum
from arista_sim.exercises import choose_study_now, evaluate_attempt, load_exercise_families
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

    def test_curriculum_has_five_source_sections_and_valid_dependencies(self):
        curriculum = load_curriculum()
        self.assertEqual(curriculum["version"], 1)
        self.assertEqual(len(curriculum["sections"]), 5)
        topic_ids = {
            topic["id"]
            for section in curriculum["sections"]
            for domain in section["domains"]
            for topic in domain["topics"]
        }
        self.assertIn("ospf-workflow", topic_ids)
        self.assertIn("acl-workflow", topic_ids)
        self.assertEqual(set(TrainingMode), {TrainingMode.LEARN, TrainingMode.RECALL, TrainingMode.ANALYZE, TrainingMode.CONFIGURE, TrainingMode.VERIFY, TrainingMode.TROUBLESHOOT})
        self.assertEqual(SkillMastery("ospf-workflow", TrainingMode.TROUBLESHOOT).mastery, 0.0)

    def test_curriculum_rejects_unknown_prerequisite(self):
        curriculum = load_curriculum()
        curriculum["sections"][0]["domains"][0]["topics"][0]["prerequisites"] = ["missing-topic"]
        with self.assertRaisesRegex(ValueError, "Unknown prerequisite"):
            validate_curriculum(curriculum)

    def test_exercise_families_evaluate_and_select_deterministically(self):
        self.assertEqual(len(load_exercise_families()), 6)
        selected = choose_study_now([])
        self.assertEqual(selected["id"], "vlan-trunk-mismatch")
        self.assertNotIn("answer", selected)
        result = evaluate_attempt("arp-next-hop", "remote-server", "10.10.10.1")
        self.assertTrue(result["correct"])


if __name__ == "__main__":
    unittest.main()
