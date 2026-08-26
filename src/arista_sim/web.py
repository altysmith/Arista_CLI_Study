from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import uuid
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any
from urllib.parse import urlparse

from .cli.session import Session
from .labs import get_lab, grade_lab, load_labs, public_lab


MAX_REQUEST_BYTES = 64 * 1024


@dataclass
class BrowserSession:
    cli: Session
    lab_id: str


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, BrowserSession] = {}
        self._lock = threading.Lock()

    def create(self, lab_id: str) -> tuple[str, BrowserSession]:
        get_lab(lab_id)
        session_id = uuid.uuid4().hex
        browser_session = BrowserSession(Session(), lab_id)
        with self._lock:
            self._sessions[session_id] = browser_session
        return session_id, browser_session

    def get(self, session_id: str) -> BrowserSession:
        with self._lock:
            try:
                return self._sessions[session_id]
            except KeyError as exc:
                raise KeyError("Browser session not found") from exc

    def reset(self, session_id: str) -> BrowserSession:
        current = self.get(session_id)
        replacement = BrowserSession(Session(), current.lab_id)
        with self._lock:
            self._sessions[session_id] = replacement
        return replacement


class LabApplication:
    def __init__(self) -> None:
        self.sessions = SessionStore()

    def labs(self) -> dict[str, Any]:
        return {"labs": [public_lab(lab) for lab in load_labs()]}

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        labs = load_labs()
        lab_id = str(payload.get("lab_id") or labs[0]["id"])
        session_id, browser_session = self.sessions.create(lab_id)
        return {
            "session_id": session_id,
            "prompt": browser_session.cli.prompt,
            "lab": public_lab(get_lab(lab_id)),
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
        return {
            "input_prompt": input_prompt,
            "command": command,
            "output": output,
            "prompt": browser_session.cli.prompt,
            "closed": browser_session.cli.closed,
        }

    def grade(self, session_id: str) -> dict[str, Any]:
        browser_session = self.sessions.get(session_id)
        return grade_lab(browser_session.cli.device, get_lab(browser_session.lab_id))

    def reset(self, session_id: str) -> dict[str, Any]:
        browser_session = self.sessions.reset(session_id)
        return {"prompt": browser_session.cli.prompt, "closed": False}


class LabRequestHandler(BaseHTTPRequestHandler):
    server_version = "AristaLab/0.1"

    @property
    def app(self) -> LabApplication:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/labs":
            self._send_json(self.app.labs())
            return
        self._send_asset("index.html" if path == "/" else path.removeprefix("/"))

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/sessions":
                self._send_json(self.app.create_session(payload), HTTPStatus.CREATED)
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
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except KeyError as error:
            self._send_json({"error": str(error)}, HTTPStatus.NOT_FOUND)
        except (json.JSONDecodeError, ValueError) as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_REQUEST_BYTES:
            raise ValueError("request is too large")
        if length == 0:
            return {}
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
        if not asset_path or ".." in asset_path.split("/"):
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
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), LabRequestHandler)
    server.app = LabApplication()  # type: ignore[attr-defined]
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the browser-based EOS practice lab")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = create_server(args.host, args.port)
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
