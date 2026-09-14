"""Versioned JSON snapshots; never deserialize executable objects or pickle."""
from dataclasses import fields, is_dataclass
from enum import Enum
from contextlib import contextmanager
import json
import sqlite3
from pathlib import Path

from .models import device
from .cli.session import Session, Mode

TYPES = {name: value for name, value in vars(device).items()
         if isinstance(value, type) and is_dataclass(value)}


def encode(value):
    if is_dataclass(value):
        return {"type": type(value).__name__, "fields": {f.name: encode(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, dict):
        return {"dict": [[encode(k), encode(v)] for k, v in value.items()]}
    if isinstance(value, (set, tuple)):
        return {type(value).__name__: [encode(v) for v in value]}
    if isinstance(value, list):
        return [encode(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    return value


def decode(value):
    if isinstance(value, list):
        return [decode(v) for v in value]
    if not isinstance(value, dict):
        return value
    if "type" in value:
        return TYPES[value["type"]](**{k: decode(v) for k, v in value["fields"].items()})
    if "dict" in value:
        return {decode(k): decode(v) for k, v in value["dict"]}
    if "set" in value:
        return set(decode(v) for v in value["set"])
    if "tuple" in value:
        return tuple(decode(v) for v in value["tuple"])
    raise ValueError("Invalid saved state")


def dump_cli(cli):
    return {"device": encode(cli.device), "mode": cli.mode.value,
            "context": encode(cli.context), "closed": cli.closed, "history": cli.history[-100:]}


def restore_cli(data, cli=None):
    cli = cli or Session()
    cli.device = decode(data["device"])
    cli.mode = Mode(data["mode"])
    cli.context = decode(data["context"])
    cli.closed = data["closed"]
    cli.history = data["history"]
    return cli


class ProgressDatabase:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, lab TEXT NOT NULL, state TEXT NOT NULL, updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        try:
            with db:
                yield db
        finally:
            db.close()

    def save(self, session_id, lab_id, state):
        with self.connect() as db:
            db.execute("INSERT INTO sessions(id,lab,state) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state, updated=CURRENT_TIMESTAMP",
                       (session_id, lab_id, json.dumps({"version": 1, **state})))

    def load(self, session_id):
        with self.connect() as db:
            row = db.execute("SELECT lab,state FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            raise KeyError("Browser session not found")
        data = json.loads(row[1])
        if data.pop("version") != 1:
            raise ValueError("Unsupported saved-state version")
        return row[0], data

    def latest(self, lab_id):
        with self.connect() as db:
            row = db.execute("SELECT id FROM sessions WHERE lab=? ORDER BY updated DESC,rowid DESC LIMIT 1", (lab_id,)).fetchone()
        return row[0] if row else None
