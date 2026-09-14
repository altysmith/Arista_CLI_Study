"""Create a consistent SQLite backup; retain the newest 14 verified backups."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def backup(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.mkdir(parents=True, exist_ok=True)
    name = "progress-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".sqlite3"
    target = destination / name
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
        if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Backup integrity check failed")
        count = dst.execute("SELECT count(*) FROM sessions").fetchone()[0]
    for old in sorted(destination.glob("progress-*.sqlite3"), reverse=True)[14:]:
        if old.resolve().parent == destination:
            old.unlink()
    print(f"Verified backup: {target.name}; saved labs: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    args = parser.parse_args()
    backup(args.source, args.destination)
