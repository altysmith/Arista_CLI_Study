"""Validated, source-grounded curriculum taxonomy for adaptive training."""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from importlib.resources import files
from typing import Any


class TrainingMode(StrEnum):
    LEARN = "learn"
    RECALL = "recall"
    ANALYZE = "analyze"
    CONFIGURE = "configure"
    VERIFY = "verify"
    TROUBLESHOOT = "troubleshoot"


@dataclass(frozen=True)
class SkillMastery:
    """In-memory contract for future persisted topic-by-mode progress."""

    topic_id: str
    mode: TrainingMode
    mastery: float = 0.0
    attempts: int = 0
    correct_attempts: int = 0
    recent_error_rate: float = 0.0
    last_practiced_at: str | None = None


PRIORITIES = {"low", "medium", "high", "very_high"}


def load_curriculum() -> dict[str, Any]:
    resource = files("arista_sim").joinpath("reference", "curriculum.json")
    curriculum = json.loads(resource.read_text(encoding="utf-8"))
    validate_curriculum(curriculum)
    return curriculum


def validate_curriculum(curriculum: dict[str, Any]) -> None:
    if curriculum.get("version") != 1:
        raise ValueError("Unsupported curriculum version")
    sections = curriculum.get("sections")
    if not isinstance(sections, list) or len(sections) != 5:
        raise ValueError("Curriculum must contain the five source sections")

    section_ids: set[str] = set()
    topic_ids: set[str] = set()
    prerequisite_ids: list[str] = []
    expected_modes = {mode.value for mode in TrainingMode}
    for section in sections:
        _required_text(section, "id", "section")
        _required_text(section, "title", "section")
        section_id = section["id"]
        if section_id in section_ids:
            raise ValueError(f"Duplicate section id: {section_id}")
        section_ids.add(section_id)
        _validate_source_refs(section.get("source_refs"), section_id)
        domains = section.get("domains")
        if not isinstance(domains, list) or not domains:
            raise ValueError(f"Section {section_id} must have domains")
        for domain in domains:
            _required_text(domain, "id", f"domain in {section_id}")
            _required_text(domain, "title", f"domain in {section_id}")
            topics = domain.get("topics")
            if not isinstance(topics, list) or not topics:
                raise ValueError(f"Domain {domain['id']} must have topics")
            for topic in topics:
                _required_text(topic, "id", f"topic in {domain['id']}")
                _required_text(topic, "title", f"topic {topic['id']}")
                topic_id = topic["id"]
                if topic_id in topic_ids:
                    raise ValueError(f"Duplicate topic id: {topic_id}")
                topic_ids.add(topic_id)
                if topic.get("priority") not in PRIORITIES:
                    raise ValueError(f"Topic {topic_id} has an invalid priority")
                modes = topic.get("modes")
                if not isinstance(modes, list) or not modes or not set(modes) <= expected_modes:
                    raise ValueError(f"Topic {topic_id} has invalid training modes")
                if len(modes) != len(set(modes)):
                    raise ValueError(f"Topic {topic_id} repeats a training mode")
                prerequisites = topic.get("prerequisites", [])
                if not isinstance(prerequisites, list) or not all(isinstance(item, str) for item in prerequisites):
                    raise ValueError(f"Topic {topic_id} has invalid prerequisites")
                prerequisite_ids.extend(prerequisites)
                _validate_source_refs(topic.get("source_refs"), topic_id)
    missing = set(prerequisite_ids) - topic_ids
    if missing:
        raise ValueError(f"Unknown prerequisite topics: {', '.join(sorted(missing))}")


def _required_text(record: dict[str, Any], key: str, label: str) -> None:
    if not isinstance(record.get(key), str) or not record[key].strip():
        raise ValueError(f"Missing {key} on {label}")


def _validate_source_refs(refs: Any, label: str) -> None:
    if not isinstance(refs, list) or not refs:
        raise ValueError(f"{label} must have source references")
    for ref in refs:
        _required_text(ref, "document", f"source reference on {label}")
        pages = ref.get("pages")
        if not isinstance(pages, list) or not pages or not all(isinstance(page, int) and page > 0 for page in pages):
            raise ValueError(f"Source reference on {label} must have positive page numbers")
