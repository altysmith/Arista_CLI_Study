import json
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

    def create_session(self):
        _, _, body = self.request("/api/sessions", {"lab_id": "access-vlan-basics"})
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

        status, _, body = self.request("/api/labs")
        catalog = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(catalog["labs"][0]["id"], "access-vlan-basics")
        self.assertNotIn("checks", catalog["labs"][0])

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

    def test_unknown_session_returns_not_found(self):
        with self.assertRaises(HTTPError) as context:
            self.request("/api/sessions/missing/grade", {})
        try:
            self.assertEqual(context.exception.code, 404)
        finally:
            context.exception.close()


if __name__ == "__main__":
    unittest.main()
