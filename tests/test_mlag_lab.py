import tempfile
import unittest
from pathlib import Path

from arista_sim.web import LabApplication
from arista_sim.labs import get_lab, grade_lab, load_labs, load_sections


REPAIR = ["enable", "configure terminal", "mlag configuration",
          "domain-id CAMPUS", "peer-address 10.255.255.2",
          "peer-link port-channel 100", "no shutdown", "exit",
          "interface Port-Channel10", "mlag 10",
          "switchport trunk allowed vlan add 20", "end"]


class MlagLabTests(unittest.TestCase):
    def setUp(self):
        self.app = LabApplication()
        self.session = self.app.create_session({"lab_id": "mlag-campus-repair"})
        self.sid = self.session["session_id"]

    def repair(self):
        for command in REPAIR:
            output = self.app.execute(self.sid, {"command": command})["output"]
            self.assertFalse(output.startswith("%"), (command, output))

    def test_repair_and_reset(self):
        self.assertEqual(self.session["prompt"], "DIST-A>")
        self.assertNotIn("setup_commands", self.session["lab"])
        self.assertNotIn("checks", self.session["lab"])
        initial = self.app.grade(self.sid)
        self.assertFalse(initial["passed"])
        self.assertEqual(initial["total_count"] - initial["passed_count"], 6)
        self.repair()
        self.assertTrue(self.app.grade(self.sid)["passed"])
        self.app.reset(self.sid)
        self.assertEqual(self.app.grade(self.sid), initial)

    def test_each_requirement_detects_regression(self):
        self.repair()
        device = self.app.sessions.get(self.sid).cli.device
        lab = get_lab("mlag-campus-repair")
        for check in lab["checks"]:
            with self.subTest(check=check["label"]):
                if check["type"] == "vlan_exists":
                    old = device.vlans.pop(check["vlan"])
                    self.assertFalse(grade_lab(device, lab)["passed"])
                    device.vlans[check["vlan"]] = old
                else:
                    target = device.mlag if check["type"] == "mlag_attribute" else device.interfaces[check["interface"]]
                    attr = check["attribute"]
                    old = getattr(target, attr)
                    setattr(target, attr, not old if isinstance(old, bool) else (99 if old is None else None))
                    self.assertFalse(grade_lab(device, lab)["passed"])
                    setattr(target, attr, old)

    def test_durable_resume_and_section_membership(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "test.sqlite3"
            self.app = LabApplication(db)
            self.sid = self.app.create_session({"lab_id": "mlag-campus-repair"})["session_id"]
            self.repair()
            restored = LabApplication(db)
            session = restored.create_session({"lab_id": "mlag-campus-repair", "resume": True})
            self.assertEqual(session["session_id"], self.sid)
            self.assertTrue(restored.grade(self.sid)["passed"])
        prep = next(s for s in load_sections() if s["id"] == "network-admin-prep")
        self.assertTrue(any("mlag-campus-repair" in topic["labs"] for topic in prep["topics"]))

    def test_l1_certification_kit_has_a_complete_practice_route(self):
        kit = next(s for s in load_sections() if s["id"] == "l1-certification-lab-kit")
        self.assertIn("not an official certification", kit["description"])
        self.assertGreaterEqual(len(kit["topics"]), 6)
        lab_ids = {lab_id for topic in kit["topics"] for lab_id in topic["labs"]}
        self.assertEqual(
            lab_ids,
            {
                "access-vlan-basics",
                "trunk-add-vlan",
                "campus-access-ticket",
                "campus-trunk-ticket",
                "mlag-campus-repair",
            },
        )
        self.assertTrue(all(topic["checkpoints"] for topic in kit["topics"]))

    def test_master_note_domains_are_available_as_l1_sections(self):
        sections = {section["id"]: section for section in load_sections()}
        expected = {
            "l1-network-engineering-fundamentals",
            "l1-eos-fundamentals",
            "l1-layer2-switching-fundamentals",
            "l1-layer3-routing-fundamentals",
            "l1-advanced-networking-concepts",
        }
        self.assertTrue(expected.issubset(sections))
        known_labs = {lab["id"] for lab in load_labs()}
        for section_id in expected:
            with self.subTest(section=section_id):
                topics = sections[section_id]["topics"]
                self.assertGreaterEqual(len(topics), 4)
                self.assertTrue(all(topic["checkpoints"] for topic in topics))
                for topic in topics:
                    self.assertTrue(set(topic["labs"]).issubset(known_labs))

    def test_mlag_grade_reports_inspection_evidence(self):
        for command in ("enable", "show running-config", "show mlag", "show port-channel dense"):
            self.app.execute(self.sid, {"command": command})
        self.assertEqual(self.app.grade(self.sid)["process_passed_count"], 3)
