from __future__ import annotations

import argparse
import json
import mimetypes
import os
import threading
import uuid
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any
from urllib.parse import parse_qs, urlparse

from .cli.session import Session
from .labs import get_lab, grade_lab, load_labs, load_sections, public_lab
from .reference import load_command_reference
from .persistence import ProgressDatabase, dump_cli, restore_cli
from .campus import Campus, RoutedCampus
from .curriculum import load_curriculum
from .exercises import choose_study_now, evaluate_attempt, exercise_choices
from .exam import build_exam, public_exam, score_exam


MAX_REQUEST_BYTES = 64 * 1024


@dataclass
class BrowserSession:
    cli: Session
    lab_id: str
    campus: Campus | RoutedCampus | None = None
    active: str = ""


class SessionStore:
    def __init__(self, data_path=None) -> None:
        self._sessions: dict[str, BrowserSession] = {}
        self._lock = threading.RLock()
        self.database = ProgressDatabase(data_path) if data_path else None

    def save(self, session_id):
        current = self.get(session_id)
        if self.database:
            self.database.save(session_id, current.lab_id, {
                "cli": dump_cli(current.cli), "active": current.active,
                "devices": {n: dump_cli(c) for n, c in current.campus.sessions.items()} if current.campus else None,
                "evidence": sorted(current.campus.evidence) if current.campus else None})

    def latest(self, lab_id):
        if self.database:
            return self.database.latest(lab_id)
        return next((sid for sid, s in reversed(list(self._sessions.items())) if s.lab_id == lab_id), None)

    def _new(self, lab):
        if lab.get("campus_fault"):
            fault = lab["campus_fault"]
            campus = RoutedCampus("static" if fault == "routing" else fault) if fault in ("routing", "next-hop", "ospf-area") else Campus(fault)
            active = next(iter(campus.sessions))
            return BrowserSession(campus.sessions[active], lab["id"], campus, active)
        return BrowserSession(self._starting_session(lab), lab["id"])

    def create(self, lab_id: str) -> tuple[str, BrowserSession]:
        lab = get_lab(lab_id)
        session_id = uuid.uuid4().hex
        browser_session = self._new(lab)
        with self._lock:
            if len(self._sessions) >= 64:
                if not self.database:
                    raise ValueError("Too many sessions; restart the local server")
                self._sessions.pop(next(iter(self._sessions)))
            self._sessions[session_id] = browser_session
            self.save(session_id)
        return session_id, browser_session

    def get(self, session_id: str) -> BrowserSession:
        with self._lock:
            if session_id not in self._sessions and self.database:
                lab_id, data = self.database.load(session_id)
                current = self._new(get_lab(lab_id))
                if current.campus:
                    for name, state in data["devices"].items():
                        restore_cli(state, current.campus.sessions[name])
                    current.campus.evidence = set(data.get("evidence") or [])
                    current.active = data["active"]
                    current.cli = current.campus.sessions[current.active]
                else:
                    current.cli = restore_cli(data["cli"])
                if len(self._sessions) >= 64:
                    self._sessions.pop(next(iter(self._sessions)))
                self._sessions[session_id] = current
            try:
                return self._sessions[session_id]
            except KeyError as exc:
                raise KeyError("Browser session not found") from exc

    def reset(self, session_id: str) -> BrowserSession:
        current = self.get(session_id)
        replacement = self._new(get_lab(current.lab_id))
        with self._lock:
            self._sessions[session_id] = replacement
            self.save(session_id)
        return replacement

    @staticmethod
    def _starting_session(lab: dict[str, Any]) -> Session:
        cli = Session()
        for command in lab.get("setup_commands", []):
            output = cli.execute(str(command))
            if output.startswith("%"):
                raise ValueError(f"Invalid setup command in {lab['id']}: {command}: {output}")
        cli.history.clear()
        return cli


class LabApplication:
    def __init__(self, data_path=None) -> None:
        self.sessions = SessionStore(data_path)

    def labs(self) -> dict[str, Any]:
        return {"labs": [public_lab(lab) for lab in load_labs()], "sections": load_sections()}

    def command_reference(self) -> dict[str, Any]:
        return load_command_reference()

    def curriculum(self) -> dict[str, Any]:
        return load_curriculum()

    def study_now(self, topic_id=None, mode=None) -> dict[str, Any]:
        progress = self.sessions.database.skill_progress() if self.sessions.database else []
        attempts = self.sessions.database.exercise_attempt_counts() if self.sessions.database else {}
        return choose_study_now(progress, topic_id=topic_id, mode=mode, family_attempts=attempts)

    def progress(self) -> dict[str, Any]:
        if not self.sessions.database:
            return {"skills": [], "recent_mistakes": []}
        return {"skills": self.sessions.database.skill_progress(), "recent_mistakes": self.sessions.database.recent_mistakes()}

    def exercises(self) -> dict[str, Any]:
        return {"exercises": exercise_choices()}

    def exam(self) -> dict[str, Any]:
        if not self.sessions.database:
            return {"active": None}
        active = self.sessions.database.active_exam()
        if active:
            return {"active": public_exam(active["questions"], active["started_at"], active["id"])}
        return {"active": None}

    def start_exam(self) -> dict[str, Any]:
        if not self.sessions.database:
            raise ValueError("Exam progress requires durable storage")
        active = self.sessions.database.active_exam()
        if active:
            return public_exam(active["questions"], active["started_at"], active["id"])
        exam_id = uuid.uuid4().hex
        questions = build_exam(exam_id)
        started_at = self.sessions.database.create_exam(exam_id, questions)
        return public_exam(questions, started_at, exam_id)

    def submit_exam(self, exam_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.sessions.database:
            raise ValueError("Exam progress requires durable storage")
        answers = payload.get("answers")
        if not isinstance(answers, list):
            raise ValueError("Exam answers must be a list")
        exam = self.sessions.database.exam(exam_id)
        if exam["submitted_at"]:
            return exam["results"]
        result = score_exam(exam["questions"], answers)
        self.sessions.database.submit_exam(exam_id, result)
        return result

    def submit_attempt(self, exercise_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.sessions.database:
            raise ValueError("Exercise progress requires durable storage")
        variant_id = payload.get("variant_id")
        answer = payload.get("answer")
        hints_used = payload.get("hints_used", 0)
        if not isinstance(variant_id, str) or not isinstance(answer, str) or not isinstance(hints_used, int) or hints_used < 0:
            raise ValueError("Invalid exercise attempt")
        result = evaluate_attempt(exercise_id, variant_id, answer)
        progress = self.sessions.database.record_attempt(exercise_id, result["topic_id"], result["mode"], result["correct"], hints_used, result["error_tags"])
        return {"correct": result["correct"], "explanation": result["explanation"], "error_tags": result["error_tags"], "progress": progress}

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        labs = load_labs()
        lab_id = str(payload.get("lab_id") or labs[0]["id"])
        session_id = self.sessions.latest(lab_id) if payload.get("resume") else None
        if session_id:
            browser_session = self.sessions.get(session_id)
        else:
            session_id, browser_session = self.sessions.create(lab_id)
        return {
            "session_id": session_id,
            "prompt": browser_session.cli.prompt,
            "lab": public_lab(get_lab(lab_id)),
            "closed": browser_session.cli.closed,
            "history": browser_session.cli.history[-100:],
            "campus": browser_session.campus.view() if browser_session.campus else None,
            "active": browser_session.active,
            "durable": self.sessions.database is not None,
        }

    def execute(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        browser_session = self.sessions.get(session_id)
        command = payload.get("command")
        if not isinstance(command, str):
            raise ValueError("command must be a string")
        if len(command) > 4096:
            raise ValueError("command is too long")
        if browser_session.cli.closed:
            raise ValueError("session is closed; reset it to continue")

        input_prompt = browser_session.cli.prompt
        output = browser_session.cli.execute(command)
        browser_session.cli.history = browser_session.cli.history[-100:]
        if browser_session.campus and command.strip() and not command.strip().startswith(("show", "ping")):
            # A topology/configuration change invalidates this simplified learning cache.
            browser_session.campus.mac = {n: {} for n in browser_session.campus.sessions}
            browser_session.campus.arp = {n: {} for n in browser_session.campus.arp}
        self.sessions.save(session_id)
        return {
            "input_prompt": input_prompt,
            "command": command,
            "output": output,
            "prompt": browser_session.cli.prompt,
            "closed": browser_session.cli.closed,
            "campus": browser_session.campus.view() if browser_session.campus else None,
            "active": browser_session.active,
        }

    def grade(self, session_id: str) -> dict[str, Any]:
        browser_session = self.sessions.get(session_id)
        if browser_session.campus:
            return browser_session.campus.grade()
        return grade_lab(browser_session.cli.device, get_lab(browser_session.lab_id), browser_session.cli.history)

    def campus_action(self, session_id, payload):
        current = self.sessions.get(session_id)
        if not current.campus:
            raise ValueError("This exercise is a single-switch lab")
        result = {}
        if "device" in payload:
            name = payload["device"]
            if name not in current.campus.sessions:
                raise ValueError("Unknown switch")
            current.active = name
            current.cli = current.campus.sessions[name]
            self.sessions.save(session_id)
        if "source" in payload:
            result = current.campus.ping(payload["source"], payload.get("destination"))
        return {**result, "campus": current.campus.view(), "active": current.active,
                "prompt": current.cli.prompt, "closed": current.cli.closed, "history": current.cli.history}

    def reset(self, session_id: str) -> dict[str, Any]:
        browser_session = self.sessions.reset(session_id)
        return {"prompt": browser_session.cli.prompt, "closed": False,
                "active": browser_session.active, "campus": browser_session.campus.view() if browser_session.campus else None}


class LabRequestHandler(BaseHTTPRequestHandler):
    server_version = "AristaLab/0.1"

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    @property
    def app(self) -> LabApplication:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        request_url = urlparse(self.path)
        path = request_url.path
        if path == "/api/labs":
            self._send_json(self.app.labs())
            return
        if path == "/api/reference":
            self._send_json(self.app.command_reference())
            return
        if path == "/api/curriculum":
            self._send_json(self.app.curriculum())
            return
        if path == "/api/study-now":
            query = parse_qs(request_url.query)
            self._send_json(self.app.study_now(query.get("topic_id", [None])[0], query.get("mode", [None])[0]))
            return
        if path == "/api/progress":
            self._send_json(self.app.progress())
            return
        if path == "/api/exercises":
            self._send_json(self.app.exercises())
            return
        if path == "/api/exam":
            self._send_json(self.app.exam())
            return
        self._send_asset("index.html" if path == "/" else path.removeprefix("/"))

    def do_POST(self) -> None:
        # Serialize operations so commands, resets, and durable snapshots cannot race.
        with self.app.sessions._lock:
            self._post()

    def _post(self) -> None:
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            self._send_json({"error": "Cross-origin requests are not allowed"}, HTTPStatus.FORBIDDEN)
            return
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/sessions":
                self._send_json(self.app.create_session(payload), HTTPStatus.CREATED)
                return

            if path == "/api/exam":
                self._send_json(self.app.start_exam(), HTTPStatus.CREATED)
                return

            if path.startswith("/api/exams/") and path.endswith("/submit"):
                parts = path.strip("/").split("/")
                if len(parts) == 4:
                    self._send_json(self.app.submit_exam(parts[2], payload))
                    return

            if path.startswith("/api/exercises/") and path.endswith("/attempts"):
                parts = path.strip("/").split("/")
                if len(parts) == 4:
                    self._send_json(self.app.submit_attempt(parts[2], payload))
                    return

            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[:2] == ["api", "sessions"]:
                session_id, action = parts[2], parts[3]
                if action == "commands":
                    self._send_json(self.app.execute(session_id, payload))
                    return
                if action == "grade":
                    self._send_json(self.app.grade(session_id))
                    return
                if action == "reset":
                    self._send_json(self.app.reset(session_id))
                    return
                if action == "help":
                    command = payload.get("command", "")
                    if not isinstance(command, str) or len(command) > 4096:
                        raise ValueError("Invalid help input")
                    cli = self.app.sessions.get(session_id).cli
                    completed, matches = cli.complete(command)
                    self._send_json({"output": cli.help(command + "?"), "completed": completed, "matches": matches})
                    return
                if action == "campus":
                    self._send_json(self.app.campus_action(session_id, payload))
                    return
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except KeyError as error:
            self._send_json({"error": str(error)}, HTTPStatus.NOT_FOUND)
        except (json.JSONDecodeError, ValueError) as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("request is too large")
        if length == 0:
            return {}
        if self.headers.get_content_type() != "application/json":
            raise ValueError("Content-Type must be application/json")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_asset(self, asset_path: str) -> None:
        if asset_path not in {"index.html", "styles.css", "app.js"}:
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        resource = files("arista_sim").joinpath("web_assets", asset_path)
        if not resource.is_file():
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        body = resource.read_bytes()
        content_type = mimetypes.guess_type(asset_path)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def create_server(host: str = "127.0.0.1", port: int = 8765, data_path=None) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), LabRequestHandler)
    server.app = LabApplication(data_path)  # type: ignore[attr-defined]
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the browser-based EOS practice lab")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--data-path", default=os.environ.get("ARISTA_DATA_PATH"), help="SQLite path for saved lab progress")
    args = parser.parse_args()

    server = create_server(args.host, args.port, args.data_path)
    host, port = server.server_address[:2]
    browser_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    url = f"http://{browser_host}:{port}"
    print(f"Arista CLI Practice Lab is running at {url}")
    print("Press Ctrl+C to stop it.")
    if not args.no_browser:
        threading.Timer(0.35, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
