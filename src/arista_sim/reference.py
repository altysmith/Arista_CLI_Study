from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


def load_command_reference() -> dict[str, Any]:
    resource = files("arista_sim").joinpath("reference", "commands.json")
    return json.loads(resource.read_text(encoding="utf-8"))
