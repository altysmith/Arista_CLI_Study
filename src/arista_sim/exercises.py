"""Declarative practice families and deterministic adaptive selection."""
from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

from .curriculum import TrainingMode, load_curriculum


PRIORITY_WEIGHTS = {"low": 1.0, "medium": 1.5, "high": 2.0, "very_high": 2.5}


def load_exercise_families() -> list[dict[str, Any]]:
    resource = files("arista_sim").joinpath("reference", "exercise_families.json")
    families = json.loads(resource.read_text(encoding="utf-8"))
    validate_exercise_families(families)
    return families


def validate_exercise_families(families: list[dict[str, Any]]) -> None:
    if not isinstance(families, list) or not families:
        raise ValueError("Exercise families must be a non-empty list")
    topic_ids = {
        topic["id"]
        for section in load_curriculum()["sections"]
        for domain in section["domains"]
        for topic in domain["topics"]
    }
    family_ids: set[str] = set()
    for family in families:
        for key in ("id", "title", "topic_id", "mode", "priority", "variants"):
            if key not in family:
                raise ValueError(f"Exercise family is missing {key}")
        if family["id"] in family_ids:
            raise ValueError(f"Duplicate exercise family id: {family['id']}")
        family_ids.add(family["id"])
        if family["topic_id"] not in topic_ids:
            raise ValueError(f"Unknown topic: {family['topic_id']}")
        if family["mode"] not in {mode.value for mode in TrainingMode}:
            raise ValueError(f"Invalid exercise mode: {family['mode']}")
        if family["priority"] not in PRIORITY_WEIGHTS:
            raise ValueError(f"Invalid exercise priority: {family['priority']}")
        variants = family["variants"]
        if not isinstance(variants, list) or not variants:
            raise ValueError(f"Exercise family {family['id']} needs variants")
        for variant in variants:
            if not all(isinstance(variant.get(key), str) and variant[key].strip() for key in ("id", "prompt", "answer", "explanation")):
                raise ValueError(f"Exercise family {family['id']} has an incomplete variant")


def public_exercise(family: dict[str, Any], variant: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "id": family["id"], "title": family["title"], "topic_id": family["topic_id"],
        "mode": family["mode"], "variant_id": variant["id"], "prompt": variant["prompt"],
        "hints": family.get("hints", []), "reason": reason,
    }


def choose_study_now(progress: list[dict[str, Any]]) -> dict[str, Any]:
    """Choose deterministically so the learner can understand and test the recommendation."""
    progress_by_skill = {(item["topic_id"], item["mode"]): item for item in progress}
    ranked: list[tuple[float, dict[str, Any], str]] = []
    for family in load_exercise_families():
        skill = progress_by_skill.get((family["topic_id"], family["mode"]))
        mastery = float(skill["mastery"]) if skill else 0.0
        error_rate = float(skill["recent_error_rate"]) if skill else 0.0
        attempts = int(skill["attempts"]) if skill else 0
        weakness = 1.0 - mastery / 100.0
        error_factor = 1.0 + error_rate
        new_skill_factor = 1.2 if attempts == 0 else 1.0
        score = PRIORITY_WEIGHTS[family["priority"]] * weakness * error_factor * new_skill_factor
        reason = (
            f"{family['priority'].replace('_', ' ')} priority; new skill"
            if attempts == 0 else
            f"{family['priority'].replace('_', ' ')} priority; {mastery:.0f}% mastery and {error_rate:.0%} recent error rate"
        )
        ranked.append((score, family, reason))
    _, family, reason = max(ranked, key=lambda item: (item[0], item[1]["id"]))
    return public_exercise(family, family["variants"][0], reason)


def evaluate_attempt(family_id: str, variant_id: str, answer: str) -> dict[str, Any]:
    family = next((item for item in load_exercise_families() if item["id"] == family_id), None)
    if family is None:
        raise KeyError("Exercise family not found")
    variant = next((item for item in family["variants"] if item["id"] == variant_id), None)
    if variant is None:
        raise ValueError("Exercise variant not found")
    correct = answer.strip().casefold() == variant["answer"].strip().casefold()
    return {
        "correct": correct, "explanation": variant["explanation"], "topic_id": family["topic_id"],
        "mode": family["mode"], "error_tags": [] if correct else family.get("error_tags", ["concept"]),
    }
