import json
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from arista_sim.web import create_server


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0)
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=2) as response:
            body = response.read()
            content_type = response.headers["Content-Type"]
            return response.status, content_type, body

    def create_session(self, lab_id="access-vlan-basics"):
        _, _, body = self.request("/api/sessions", {"lab_id": lab_id})
        return json.loads(body)

    def command(self, session_id, command):
        _, _, body = self.request(
            f"/api/sessions/{session_id}/commands", {"command": command}
        )
        return json.loads(body)

    def test_serves_browser_application_and_lab_catalog(self):
        status, content_type, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn(b"Arista CLI Lab", body)
        self.assertIn(b"Command reference", body)

        status, _, body = self.request("/api/labs")
        catalog = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(catalog["labs"][0]["id"], "access-vlan-basics")
        self.assertGreaterEqual(len(catalog["labs"]), 4)
        self.assertNotIn("checks", catalog["labs"][0])
        self.assertNotIn("setup_commands", catalog["labs"][1])

        status, _, body = self.request("/api/reference")
        reference = json.loads(body)
        self.assertEqual(status, 200)
        commands = [
            item["command"]
            for category in reference["categories"]
            for item in category["commands"]
        ]
        self.assertIn("show interfaces trunk", commands)

        status, _, body = self.request("/api/exercises")
        choices = json.loads(body)["exercises"]
        self.assertEqual(status, 200)
        self.assertIn("arp-next-hop", [choice["id"] for choice in choices])

        status, _, body = self.request("/api/study-now?topic_id=ipv4-local-delivery&mode=analyze")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["id"], "subnet-local-or-remote")

        status, _, body = self.request("/api/curriculum")
        curriculum = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(curriculum["version"], 1)
        self.assertEqual(len(curriculum["sections"]), 5)
        self.assertEqual(curriculum["sections"][0]["id"], "advanced-networking-concepts")

    def test_terminal_api_preserves_prompts_and_state(self):
        session = self.create_session()
        session_id = session["session_id"]
        self.assertEqual(session["prompt"], "switch>")

        result = self.command(session_id, "enable")
        self.assertEqual(result["input_prompt"], "switch>")
        self.assertEqual(result["prompt"], "switch#")

        result = self.command(session_id, "show vlan")
        self.assertIn("default", result["output"])

    def test_lab_can_be_completed_and_reset_through_api(self):
        session = self.create_session()
        session_id = session["session_id"]
        _, _, body = self.request(f"/api/sessions/{session_id}/grade", {})
        self.assertFalse(json.loads(body)["passed"])

        for command in (
            "enable",
            "configure terminal",
            "vlan 20",
            "name USERS",
            "exit",
            "interface Ethernet1",
            "switchport mode access",
            "switchport access vlan 20",
            "no shutdown",
            "end",
        ):
            self.command(session_id, command)

        _, _, body = self.request(f"/api/sessions/{session_id}/grade", {})
        grade = json.loads(body)
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["passed_count"], 5)

        self.request(f"/api/sessions/{session_id}/reset", {})
        _, _, body = self.request(f"/api/sessions/{session_id}/grade", {})
        self.assertFalse(json.loads(body)["passed"])

    def test_existing_trunk_lab_loads_grades_and_resets_starting_state(self):
        session = self.create_session("trunk-add-vlan")
        session_id = session["session_id"]
        self.assertEqual(session["prompt"], "switch>")

        self.command(session_id, "enable")
        initial = self.command(session_id, "show interfaces Ethernet48 switchport")
        self.assertIn("Trunking VLANs Enabled: 10,20", initial["output"])

        for command in (
            "configure terminal",
            "interface Ethernet48",
            "switchport trunk allowed vlan add 30",
            "end",
        ):
            self.command(session_id, command)

        _, _, body = self.request(f"/api/sessions/{session_id}/grade", {})
        self.assertTrue(json.loads(body)["passed"])

        self.request(f"/api/sessions/{session_id}/reset", {})
        _, _, body = self.request(f"/api/sessions/{session_id}/grade", {})
        reset_grade = json.loads(body)
        self.assertFalse(reset_grade["passed"])
        self.assertEqual(reset_grade["passed_count"], 2)

    def test_unknown_session_returns_not_found(self):
        with self.assertRaises(HTTPError) as context:
            self.request("/api/sessions/missing/grade", {})
        try:
            self.assertEqual(context.exception.code, 404)
        finally:
            context.exception.close()

    def test_campus_ticket_can_be_repaired_through_http(self):
        session = self.create_session("campus-trunk-ticket")
        self.assertNotIn("campus_fault", session["lab"])
        self.assertEqual(len(session["campus"]["hosts"]), 4)
        sid = session["session_id"]
        self.request(f"/api/sessions/{sid}/campus", {"device": "ACCESS-B"})
        for cmd in ["enable", "configure terminal", "interface Ethernet48", "switchport trunk allowed vlan add 20", "end"]:
            self.assertFalse(self.command(sid, cmd)["output"].startswith("%"))
        _, _, body = self.request(f"/api/sessions/{sid}/grade", {})
        self.assertTrue(json.loads(body)["passed"])
        _, _, body = self.request(f"/api/sessions/{sid}/campus", {"source": "STUDENT-A", "destination": "STUDENT-B"})
        self.assertTrue(json.loads(body)["success"])

    def test_help_does_not_execute_command(self):
        sid = self.create_session()["session_id"]
        _, _, body = self.request(f"/api/sessions/{sid}/help", {"command": "en"})
        self.assertIn("enable", json.loads(body)["output"])
        self.assertEqual(self.server.app.sessions.get(sid).cli.prompt, "switch>")

    def test_cross_origin_mutation_is_rejected(self):
        request = Request(self.base_url + "/api/sessions", data=b"{}", headers={"Content-Type": "application/json", "Origin": "https://unrelated.example"})
        with self.assertRaises(HTTPError) as context:
            urlopen(request, timeout=2)
        self.assertEqual(context.exception.code, 403)
        context.exception.close()

    def test_study_now_and_durable_exercise_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            server = create_server(port=0, data_path=f"{directory}/progress.sqlite3")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base_url = f"http://127.0.0.1:{server.server_port}"
                with urlopen(base_url + "/api/study-now", timeout=2) as response:
                    exercise = json.loads(response.read())
                self.assertEqual(exercise["id"], "vlan-trunk-mismatch")
                request = Request(base_url + "/api/exercises/acl-first-match/attempts", data=json.dumps({"variant_id": "specific-before-general", "answer": "permitted", "hints_used": 0}).encode("utf-8"), headers={"Content-Type": "application/json"})
                with urlopen(request, timeout=2) as response:
                    attempt = json.loads(response.read())
                self.assertTrue(attempt["correct"])
                self.assertEqual(attempt["progress"]["mastery"], 100.0)
                with urlopen(base_url + "/api/progress", timeout=2) as response:
                    self.assertEqual(json.loads(response.read())["skills"][0]["topic_id"], "acl-workflow")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
