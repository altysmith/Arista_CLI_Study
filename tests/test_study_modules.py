import tempfile
import unittest
from pathlib import Path

from arista_sim.persistence import ProgressDatabase
from arista_sim.study_modules import load_study_modules


class StudyModuleTests(unittest.TestCase):
    def test_all_authoritative_drive_modules_are_available(self):
        catalog = load_study_modules()
        self.assertEqual(catalog["module_count"], 88)
        self.assertEqual([len(section["modules"]) for section in catalog["sections"]], [20, 16, 21, 14, 17])
        self.assertEqual(catalog["sections"][1]["modules"][-1]["number"], 16)
        self.assertEqual(catalog["sections"][1]["modules"][-1]["kind"], "lab")

    def test_network_fundamentals_has_complete_interactive_structure(self):
        section = load_study_modules()["sections"][0]
        self.assertEqual(len(section["modules"]), 20)
        for module in section["modules"]:
            activities = module["activities"]
            self.assertTrue(activities["learn"], module["id"])
            self.assertTrue(activities["flashcards"], module["id"])
            self.assertTrue(activities["quiz"], module["id"])
            self.assertTrue(activities["practical"], module["id"])
            self.assertTrue(activities["mastery"], module["id"])
            self.assertTrue(all(card["question"] and card["answer"] for card in activities["flashcards"]))

    def test_module_activity_progress_round_trips_without_touching_lab_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            database = ProgressDatabase(Path(directory) / "progress.sqlite3")
            state = {"learn_reviewed": True, "flashcards_revealed": [0], "quiz_answers": ["answer"], "quiz_correct": [False], "practical_complete": False, "practical_notes": "notes", "mastery_checked": []}
            stored = database.save_study_progress("network-engineering-fundamentals:01-introduction-to-networks", state)
            self.assertTrue(stored["learn_reviewed"])
            self.assertEqual(database.study_progress()["network-engineering-fundamentals:01-introduction-to-networks"]["practical_notes"], "notes")
            self.assertEqual(database.latest("access-vlan-basics"), None)
