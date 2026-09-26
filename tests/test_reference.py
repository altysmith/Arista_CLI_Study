import unittest
import tempfile
from datetime import datetime, timezone

from arista_sim.curriculum import SkillMastery, TrainingMode, load_curriculum, validate_curriculum
from arista_sim.exercises import choose_study_now, evaluate_attempt, load_exercise_families
from arista_sim.web import LabApplication
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
        self.assertEqual(len(load_exercise_families()), 13)
        selected = choose_study_now([])
        self.assertEqual(selected["id"], "vlan-trunk-mismatch")
        self.assertNotIn("answer", selected)
        result = evaluate_attempt("arp-next-hop", "remote-server", "10.10.10.1")
        self.assertTrue(result["correct"])
        self.assertTrue(evaluate_attempt("static-default-route", "gateway-192-0-2-1", "ip route 0.0.0.0/0 192.0.2.1")["correct"])
        self.assertEqual(choose_study_now([], topic_id="stp-lacp-mlag", mode="analyze")["lab_id"], "mlag-campus-repair")
        alternate = choose_study_now([{"topic_id": "ipv4-local-delivery", "mode": "analyze", "mastery": 0, "attempts": 1, "recent_error_rate": 1, "last_practiced_at": "2026-09-25 00:00:00"}], topic_id="ipv4-local-delivery", mode="analyze", family_attempts={"subnet-local-or-remote": 1})
        self.assertEqual(alternate["variant_id"], "different-24")

    def test_study_now_exposes_adaptive_factors(self):
        selected = choose_study_now([{"topic_id": "ospf-workflow", "mode": "verify", "mastery": 20, "attempts": 3, "recent_error_rate": 1, "last_practiced_at": "2026-09-01 00:00:00"}], datetime(2026, 9, 25, tzinfo=timezone.utc))
        self.assertIn("factors", selected)
        self.assertGreaterEqual(selected["factors"]["recency"], 1)

    def test_integrated_exam_persists_and_returns_remediation(self):
        with tempfile.TemporaryDirectory() as directory:
            app = LabApplication(f"{directory}/progress.sqlite3")
            exam = app.start_exam()
            self.assertEqual(exam["question_count"], 8)
            self.assertEqual(app.exam()["active"]["id"], exam["id"])
            families = {family["id"]: family for family in load_exercise_families()}
            stored = app.sessions.database.exam(exam["id"])["questions"]
            answers = [next(variant["answer"] for variant in families[question["exercise_id"]]["variants"] if variant["id"] == stored[index]["variant_id"]) for index, question in enumerate(exam["questions"])]
            result = app.submit_exam(exam["id"], {"answers": answers})
            self.assertEqual(result["score"], result["total"])
            self.assertEqual(result["remediation"], [])
            retry = app.start_exam()
            missed = app.submit_exam(retry["id"], {"answers": ["wrong"] * retry["question_count"]})
            self.assertIn("exercise_id", missed["remediation"][0])


if __name__ == "__main__":
    unittest.main()
