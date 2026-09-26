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
            db.execute("CREATE TABLE IF NOT EXISTS exercise_attempts (id INTEGER PRIMARY KEY, exercise_id TEXT NOT NULL, topic_id TEXT NOT NULL, mode TEXT NOT NULL, correct INTEGER NOT NULL, hints_used INTEGER NOT NULL DEFAULT 0, error_tags TEXT NOT NULL DEFAULT '[]', practiced TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            db.execute("CREATE TABLE IF NOT EXISTS skill_mastery (topic_id TEXT NOT NULL, mode TEXT NOT NULL, mastery REAL NOT NULL, attempts INTEGER NOT NULL, correct_attempts INTEGER NOT NULL, recent_error_rate REAL NOT NULL, last_practiced_at TEXT NOT NULL, PRIMARY KEY(topic_id, mode))")

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

    def skill_progress(self):
        with self.connect() as db:
            rows = db.execute("SELECT topic_id,mode,mastery,attempts,correct_attempts,recent_error_rate,last_practiced_at FROM skill_mastery ORDER BY last_practiced_at DESC,topic_id,mode").fetchall()
        keys = ("topic_id", "mode", "mastery", "attempts", "correct_attempts", "recent_error_rate", "last_practiced_at")
        return [dict(zip(keys, row)) for row in rows]

    def recent_mistakes(self, limit=8):
        with self.connect() as db:
            rows = db.execute("SELECT exercise_id,topic_id,mode,error_tags,practiced FROM exercise_attempts WHERE correct=0 ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"exercise_id": row[0], "topic_id": row[1], "mode": row[2], "error_tags": json.loads(row[3]), "practiced_at": row[4]} for row in rows]

    def exercise_attempt_counts(self):
        with self.connect() as db:
            rows = db.execute("SELECT exercise_id,COUNT(*) FROM exercise_attempts GROUP BY exercise_id").fetchall()
        return {exercise_id: attempts for exercise_id, attempts in rows}

    def record_attempt(self, exercise_id, topic_id, mode, correct, hints_used, error_tags):
        with self.connect() as db:
            db.execute("INSERT INTO exercise_attempts(exercise_id,topic_id,mode,correct,hints_used,error_tags) VALUES(?,?,?,?,?,?)", (exercise_id, topic_id, mode, int(correct), hints_used, json.dumps(error_tags)))
            attempts, correct_attempts, effective_correct = db.execute("SELECT COUNT(*), COALESCE(SUM(correct),0), COALESCE(SUM(CASE WHEN correct THEN 1.0 - MIN(hints_used, 3) * 0.1 ELSE 0 END),0) FROM exercise_attempts WHERE topic_id=? AND mode=?", (topic_id, mode)).fetchone()
            recent = db.execute("SELECT correct FROM exercise_attempts WHERE topic_id=? AND mode=? ORDER BY id DESC LIMIT 5", (topic_id, mode)).fetchall()
            recent_error_rate = 1 - sum(row[0] for row in recent) / len(recent)
            mastery = round(100 * effective_correct / attempts, 1)
            db.execute("INSERT INTO skill_mastery(topic_id,mode,mastery,attempts,correct_attempts,recent_error_rate,last_practiced_at) VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(topic_id,mode) DO UPDATE SET mastery=excluded.mastery,attempts=excluded.attempts,correct_attempts=excluded.correct_attempts,recent_error_rate=excluded.recent_error_rate,last_practiced_at=excluded.last_practiced_at", (topic_id, mode, mastery, attempts, correct_attempts, recent_error_rate))
        return {"topic_id": topic_id, "mode": mode, "mastery": mastery, "attempts": attempts, "correct_attempts": correct_attempts, "recent_error_rate": recent_error_rate}
