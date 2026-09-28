"""Packaged Markdown curriculum imported from the authoritative Drive folders."""
from __future__ import annotations

import re
from importlib.resources import files
from typing import Any


SECTION_SOURCES = (
    ("network-engineering-fundamentals", "Network Engineering Fundamentals"),
    ("arista-eos-fundamentals", "Arista EOS Fundamentals"),
    ("layer-2-switching-fundamentals", "Layer 2 Switching Fundamentals"),
    ("layer-3-routing-fundamentals", "Layer 3 Routing Fundamentals"),
    ("advanced-networking-concepts", "Advanced Networking Concepts"),
)
MODULE_FILENAME = re.compile(r"^(?P<number>\d{2})-(?P<slug>[a-z0-9-]+)\.md$")
TITLE = re.compile(r"^#\s+(?:(?P<number>\d+)\.\s+)?(?P<title>.+?)\s*$", re.MULTILINE)


def load_study_modules() -> dict[str, Any]:
    """Return the five handoff-ordered sections and every numbered module."""
    root = files("arista_sim").joinpath("reference", "study_modules")
    sections = []
    module_ids: set[str] = set()
    for section_id, title in SECTION_SOURCES:
        folder = root.joinpath(section_id)
        names = sorted(item.name for item in folder.iterdir() if item.is_file() and item.name.endswith(".md"))
        if "00-curriculum-map.md" not in names:
            raise ValueError(f"{section_id} is missing 00-curriculum-map.md")
        modules = []
        for name in names:
            match = MODULE_FILENAME.match(name)
            if not match:
                raise ValueError(f"Unexpected curriculum file: {section_id}/{name}")
            number = int(match["number"])
            if number == 0:
                continue
            markdown = folder.joinpath(name).read_text(encoding="utf-8")
            heading = TITLE.search(markdown)
            if not heading:
                raise ValueError(f"{section_id}/{name} is missing a title")
            module_id = f"{section_id}:{match['number']}-{match['slug']}"
            if module_id in module_ids:
                raise ValueError(f"Duplicate curriculum module: {module_id}")
            module_ids.add(module_id)
            module_title = heading["title"]
            is_lab = module_title.upper().startswith("LAB") or "# Lab Goal" in markdown
            modules.append({
                "id": module_id,
                "number": number,
                "title": module_title,
                "kind": "lab" if is_lab else "lesson",
                "markdown": markdown,
            })
        if not modules:
            raise ValueError(f"{section_id} has no learner modules")
        sections.append({"id": section_id, "title": title, "modules": modules})
    return {"version": 1, "sections": sections, "module_count": len(module_ids)}
