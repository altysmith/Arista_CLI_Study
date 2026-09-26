import tempfile
import unittest
from pathlib import Path

from arista_sim.campus import Campus
from arista_sim.web import LabApplication


class CampusTests(unittest.TestCase):
    def test_healthy_forwarding_learns_mac_and_host_arp(self):
        campus = Campus()
        self.assertTrue(campus.grade()["passed"])
        self.assertTrue(campus.ping("STAFF-A", "STAFF-B")["success"])
        self.assertIn("10.10.10.12", campus.arp["STAFF-A"])
        self.assertIn("02:00:00:00:10:11", campus.sessions["DIST-1"].execute("show mac address-table"))
        self.assertIn("ACCESS-A", campus.sessions["DIST-1"].execute("show lldp neighbors"))
        self.assertFalse(campus.ping("STAFF-A", "STUDENT-A")["success"])

    def test_trunk_fault_repair_preserves_other_vlans(self):
        campus = Campus("trunk")
        self.assertTrue(campus.ping("STAFF-A", "STAFF-B")["success"])
        self.assertFalse(campus.ping("STUDENT-A", "STUDENT-B")["success"])
        cli = campus.sessions["ACCESS-B"]
        for command in ["enable", "configure terminal", "interface Ethernet48", "switchport trunk allowed vlan add 20", "end"]:
            self.assertFalse(cli.execute(command).startswith("%"))
        self.assertTrue(campus.grade()["passed"])
        cli.device.interfaces["Ethernet48"].allowed_vlans = {20}
        self.assertFalse(campus.grade()["passed"])

    def test_access_fault_and_vlan_isolation(self):
        campus = Campus("access")
        self.assertFalse(campus.grade()["passed"])
        campus.sessions["ACCESS-A"].device.interfaces["Ethernet1"].access_vlan = 10
        self.assertTrue(campus.grade()["passed"])
        campus.sessions["ACCESS-A"].device.interfaces["Ethernet2"].access_vlan = 10
        self.assertFalse(campus.grade()["results"][2]["passed"])

    def test_shutdown_deleted_vlan_and_native_mismatch_block_traffic(self):
        for change in ("shutdown", "vlan", "native"):
            campus = Campus()
            port = campus.sessions["ACCESS-B"].device.interfaces["Ethernet48"]
            if change == "shutdown":
                port.admin_up = False
                self.assertNotIn("ACCESS-B", campus.sessions["DIST-1"].execute("show lldp neighbors"))
            elif change == "vlan":
                del campus.sessions["DIST-1"].device.vlans[10]
            else:
                port.native_vlan = 10
            self.assertFalse(campus.ping("STAFF-A", "STAFF-B")["success"])

    def test_grading_does_not_create_learning(self):
        campus = Campus()
        campus.grade()
        self.assertTrue(all(not entries for entries in campus.mac.values()))
        self.assertTrue(all(not entries for entries in campus.arp.values()))

    def test_campus_grade_reports_evidence_without_blocking_a_correct_repair(self):
        campus = Campus("trunk")
        campus.ping("STUDENT-A", "STUDENT-B")
        cli = campus.sessions["ACCESS-B"]
        for command in ["enable", "show lldp neighbors", "show interfaces trunk", "configure terminal", "interface Ethernet48", "switchport trunk allowed vlan add 20", "end"]:
            cli.execute(command)
        grade = campus.grade()
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["process_passed_count"], 3)

    def test_campus_evidence_survives_durable_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "progress.sqlite3"
            app = LabApplication(path)
            session = app.create_session({"lab_id": "campus-trunk-ticket"})
            sid = session["session_id"]
            app.campus_action(sid, {"source": "STUDENT-A", "destination": "STUDENT-B"})
            app.execute(sid, {"command": "enable"})
            app.execute(sid, {"command": "show lldp neighbors"})
            app.execute(sid, {"command": "show interfaces trunk"})
            resumed = LabApplication(path)
            self.assertEqual(resumed.grade(sid)["process_passed_count"], 3)

    def test_access_ticket_rewards_interface_evidence_not_trunk_evidence(self):
        campus = Campus("access")
        campus.ping("STAFF-A", "STAFF-B")
        cli = campus.sessions["ACCESS-A"]
        for command in ["enable", "show lldp neighbors", "show interfaces status"]:
            cli.execute(command)
        self.assertEqual(campus.grade()["process_passed_count"], 3)

    def test_server_restart_resumes_all_switches_and_reset_persists(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "progress.sqlite3"
            app = LabApplication(path)
            created = app.create_session({"lab_id": "campus-trunk-ticket", "resume": True})
            sid = created["session_id"]
            app.campus_action(sid, {"device": "ACCESS-B"})
            for command in ["enable", "configure terminal", "interface Ethernet48", "switchport trunk allowed vlan add 20", "end", "copy running-config startup-config"]:
                app.execute(sid, {"command": command})
            restored = LabApplication(path)
            resume = restored.create_session({"lab_id": "campus-trunk-ticket", "resume": True})
            self.assertEqual(resume["session_id"], sid)
            self.assertEqual(resume["active"], "ACCESS-B")
            self.assertTrue(restored.grade(sid)["passed"])
            self.assertIsNotNone(restored.sessions.get(sid).cli.device.startup)
            restored.reset(sid)
            again = LabApplication(path)
            self.assertFalse(again.grade(sid)["passed"])

    def test_single_switch_persistence_keeps_modes_and_startup_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "progress.sqlite3"
            app = LabApplication(path)
            sid = app.create_session({"lab_id": "access-vlan-basics"})["session_id"]
            for cmd in ["enable", "configure terminal", "vlan 20", "name USERS", "end", "write", "configure terminal", "vlan 20", "name CHANGED"]:
                app.execute(sid, {"command": cmd})
            cli = LabApplication(path).sessions.get(sid).cli
            self.assertEqual(cli.prompt, "switch(config-vlan-20)#")
            self.assertEqual(cli.device.vlans[20].name, "CHANGED")
            self.assertEqual(cli.device.startup.state.vlans[20].name, "USERS")
