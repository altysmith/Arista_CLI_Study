"""Declarative practice families and deterministic adaptive selection."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from importlib.resources import files
from typing import Any

from .curriculum import TrainingMode, load_curriculum


PRIORITY_WEIGHTS = {"low": 1.0, "medium": 1.5, "high": 2.0, "very_high": 2.5}


def load_exercise_families() -> list[dict[str, Any]]:
    resource = files("arista_sim").joinpath("reference", "exercise_families.json")
    families = json.loads(resource.read_text(encoding="utf-8"))
    validate_exercise_families(families)
    return families


def exercise_choices() -> list[dict[str, str]]:
    return [{"id": family["id"], "title": family["title"], "topic_id": family["topic_id"], "mode": family["mode"]} for family in load_exercise_families()]


def validate_exercise_families(families: list[dict[str, Any]]) -> None:
    if not isinstance(families, list) or not families:
        raise ValueError("Exercise families must be a non-empty list")
    topics = {
        topic["id"]: topic
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
        if family["topic_id"] not in topics:
            raise ValueError(f"Unknown topic: {family['topic_id']}")
        if family["mode"] not in {mode.value for mode in TrainingMode}:
            raise ValueError(f"Invalid exercise mode: {family['mode']}")
        if family["mode"] not in topics[family["topic_id"]]["modes"]:
            raise ValueError(f"Exercise mode is not supported by topic: {family['id']}")
        if family["priority"] not in PRIORITY_WEIGHTS:
            raise ValueError(f"Invalid exercise priority: {family['priority']}")
        variants = family["variants"]
        if not isinstance(variants, list) or not variants:
            raise ValueError(f"Exercise family {family['id']} needs variants")
        for variant in variants:
            if not all(isinstance(variant.get(key), str) and variant[key].strip() for key in ("id", "prompt", "answer", "explanation")):
                raise ValueError(f"Exercise family {family['id']} has an incomplete variant")


def public_exercise(family: dict[str, Any], variant: dict[str, Any], reason: str, factors: dict[str, float] | None = None) -> dict[str, Any]:
    return {
        "id": family["id"], "title": family["title"], "topic_id": family["topic_id"],
        "mode": family["mode"], "variant_id": variant["id"], "prompt": variant["prompt"], "lab_id": family.get("lab_id"),
        "hints": family.get("hints", []), "reason": reason, "factors": factors or {},
    }


def choose_study_now(progress: list[dict[str, Any]], now: datetime | None = None, topic_id: str | None = None, mode: str | None = None) -> dict[str, Any]:
    """Choose deterministically so the learner can understand and test the recommendation."""
    now = now or datetime.now(timezone.utc)
    progress_by_skill = {(item["topic_id"], item["mode"]): item for item in progress}
    topics = {topic["id"]: topic for section in load_curriculum()["sections"] for domain in section["domains"] for topic in domain["topics"]}
    dependents = {topic_id: [] for topic_id in topics}
    for topic in topics.values():
        for prerequisite in topic["prerequisites"]:
            dependents[prerequisite].append(topic["id"])
    ranked: list[tuple[float, dict[str, Any], str, dict[str, float]]] = []
    for family in load_exercise_families():
        if topic_id and family["topic_id"] != topic_id:
            continue
        if mode and family["mode"] != mode:
            continue
        skill = progress_by_skill.get((family["topic_id"], family["mode"]))
        mastery = float(skill["mastery"]) if skill else 0.0
        error_rate = float(skill["recent_error_rate"]) if skill else 0.0
        attempts = int(skill["attempts"]) if skill else 0
        weakness = 1.0 - mastery / 100.0
        recency = _recency_factor(skill.get("last_practiced_at") if skill else None, now)
        dependent_need = max((_topic_need(topic_id, progress_by_skill) for topic_id in dependents[family["topic_id"]]), default=0.0)
        dependency = 1.0 + dependent_need * 0.5
        score = PRIORITY_WEIGHTS[family["priority"]] * weakness * (1.0 + error_rate) * recency * dependency
        factors = {"priority": PRIORITY_WEIGHTS[family["priority"]], "weakness": round(weakness, 2), "recency": round(recency, 2), "recent_errors": round(error_rate, 2), "dependency": round(dependency, 2)}
        reason = f"{family['priority'].replace('_', ' ')} priority; " + ("new skill" if attempts == 0 else f"{mastery:.0f}% mastery")
        if recency > 1: reason += "; due for review"
        if dependent_need: reason += "; supports a weak dependent topic"
        ranked.append((score, family, reason, factors))
    if not ranked:
        raise ValueError("No practice family matches that topic and mode")
    _, family, reason, factors = max(ranked, key=lambda item: (item[0], item[1]["id"]))
    return public_exercise(family, family["variants"][0], reason, factors)


def _topic_need(topic_id: str, progress_by_skill: dict[tuple[str, str], dict[str, Any]]) -> float:
    values = [item for (candidate, _), item in progress_by_skill.items() if candidate == topic_id]
    return max(((1 - float(item["mastery"]) / 100) * float(item["recent_error_rate"]) for item in values), default=0.0)


def _recency_factor(last_practiced_at: str | None, now: datetime) -> float:
    if not last_practiced_at: return 1.2
    practiced = datetime.fromisoformat(last_practiced_at.replace(" ", "T")).replace(tzinfo=timezone.utc)
    return 1.0 + min(max(0.0, (now - practiced).total_seconds() / 86400) / 14, 0.5)


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
