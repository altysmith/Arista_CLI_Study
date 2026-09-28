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
TOP_LEVEL_SECTION = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


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
                "activities": _parse_activities(markdown) if section_id == "network-engineering-fundamentals" else None,
            })
        if not modules:
            raise ValueError(f"{section_id} has no learner modules")
        sections.append({"id": section_id, "title": title, "modules": modules})
    return {"version": 1, "sections": sections, "module_count": len(module_ids)}


def _parse_activities(markdown: str) -> dict[str, Any]:
    """Parse the handoff activity headings without rewriting source content."""
    matches = list(TOP_LEVEL_SECTION.finditer(markdown))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches[1:], start=1):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections[match.group(1).strip().lower()] = markdown[match.end():end].strip()

    required = ("learn", "flashcards", "knowledge quiz", "practical exercise", "mastery check")
    missing = [name for name in required if not sections.get(name)]
    if missing:
        raise ValueError(f"Module is missing required activities: {', '.join(missing)}")

    flashcards = []
    for block in re.split(r"\n(?=\*\*)", sections["flashcards"]):
        match = re.match(r"\*\*(.+?)\*\*\s*(.+)", block.strip(), re.DOTALL)
        if match:
            flashcards.append({"question": match.group(1).strip(), "answer": match.group(2).strip()})
    quiz = [match.group(1).strip() for match in re.finditer(r"^\d+\.\s+(.+)$", sections["knowledge quiz"], re.MULTILINE)]
    mastery = [match.group(1).strip() for match in re.finditer(r"^-\s+\[[ xX]\]\s+(.+)$", sections["mastery check"], re.MULTILINE)]
    if not flashcards or not quiz or not mastery:
        raise ValueError("Module activities must include flashcards, quiz questions, and mastery checks")
    return {
        "learn": sections["learn"],
        "flashcards": flashcards,
        "quiz": quiz,
        "practical": sections["practical exercise"],
        "mastery": mastery,
    }


def study_module_ids() -> set[str]:
    return {module["id"] for section in load_study_modules()["sections"] for module in section["modules"]}


def study_module_lookup() -> dict[str, dict[str, Any]]:
    return {module["id"]: module for section in load_study_modules()["sections"] for module in section["modules"]}
