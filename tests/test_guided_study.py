import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from arista_sim.guided_study import guided_catalog, valid_guided_answer
from arista_sim.persistence import ProgressDatabase


class GuidedStudyTests(unittest.TestCase):
    def test_every_curriculum_topic_has_recall_and_required_application(self):
        catalog = guided_catalog([], {}, {})
        self.assertEqual(catalog["topics"][0]["id"], "ethernet-forwarding")
        self.assertTrue(all(topic["questions"] and topic["lab_id"] for topic in catalog["topics"]))

    def test_question_belongs_to_its_guided_topic(self):
        topic = next(item for item in guided_catalog([], {}, {})["topics"] if item["id"] == "vlan-trunks")
        question = topic["questions"][0]
        self.assertTrue(valid_guided_answer("vlan-trunks", question["id"], question["variant_id"]))
        self.assertFalse(valid_guided_answer("route-selection", question["id"], question["variant_id"]))

    def test_completion_history_survives_a_repeat(self):
        with TemporaryDirectory() as directory:
            database = ProgressDatabase(Path(directory) / "progress.sqlite3")
            database.complete_guided_topic("ethernet-forwarding", "Ethernet")
            completion = database.complete_guided_topic("ethernet-forwarding", "Ethernet")
        self.assertEqual(completion["completions"], 2)
