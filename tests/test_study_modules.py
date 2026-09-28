import unittest

from arista_sim.study_modules import load_study_modules


class StudyModuleTests(unittest.TestCase):
    def test_all_authoritative_drive_modules_are_available(self):
        catalog = load_study_modules()
        self.assertEqual(catalog["module_count"], 88)
        self.assertEqual([len(section["modules"]) for section in catalog["sections"]], [20, 16, 21, 14, 17])
        self.assertEqual(catalog["sections"][1]["modules"][-1]["number"], 16)
        self.assertEqual(catalog["sections"][1]["modules"][-1]["kind"], "lab")
