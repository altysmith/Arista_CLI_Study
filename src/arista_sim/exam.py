"""Persistent, varied readiness exams built from the reviewed exercise families."""
from __future__ import annotations

from typing import Any

from .exercises import evaluate_attempt, load_exercise_families


EXAM_FAMILY_IDS = (
    "subnet-local-or-remote", "vlan-trunk-mismatch", "route-selection", "eos-config-state",
    "lacp-compatibility", "static-default-route", "ospf-first-failed-dependency", "acl-first-match",
)


def build_exam(seed: str = "0") -> list[dict[str, str]]:
    families = {family["id"]: family for family in load_exercise_families()}
    questions = []
    offset = sum(seed.encode("utf-8"))
    for index, family_id in enumerate(EXAM_FAMILY_IDS):
        family = families[family_id]
        variant = family["variants"][(offset + index) % len(family["variants"])]
        questions.append({"exercise_id": family_id, "variant_id": variant["id"]})
    return questions


def public_exam(questions: list[dict[str, str]], started_at: str, exam_id: str) -> dict[str, Any]:
    families = {family["id"]: family for family in load_exercise_families()}
    items = []
    for question in questions:
        family = families[question["exercise_id"]]
        variant = next(item for item in family["variants"] if item["id"] == question["variant_id"])
        items.append({"exercise_id": family["id"], "topic_id": family["topic_id"], "mode": family["mode"], "title": family["title"], "prompt": variant["prompt"]})
    return {"id": exam_id, "started_at": started_at, "questions": items, "question_count": len(items)}


def score_exam(questions: list[dict[str, str]], answers: list[str]) -> dict[str, Any]:
    if len(answers) != len(questions) or not all(isinstance(answer, str) for answer in answers):
        raise ValueError("An answer is required for every exam question")
    families = load_exercise_families()
    results = []
    remediation: dict[str, dict[str, Any]] = {}
    for question, answer in zip(questions, answers):
        result = evaluate_attempt(question["exercise_id"], question["variant_id"], answer)
        results.append({"topic_id": result["topic_id"], "mode": result["mode"], "correct": result["correct"], "explanation": result["explanation"]})
        if not result["correct"]:
            item = remediation.setdefault(result["topic_id"], {"topic_id": result["topic_id"], "missed": 0, "modes": set()})
            item["missed"] += 1
            item["modes"].add(result["mode"])
    remediation_items = []
    for item in remediation.values():
        recommendation = next(family for family in families if family["topic_id"] == item["topic_id"])
        remediation_items.append({**item, "modes": sorted(item["modes"]), "exercise_id": recommendation["id"],
                                  "mode": recommendation["mode"], "lab_id": recommendation.get("lab_id")})
    return {"score": sum(item["correct"] for item in results), "total": len(results), "results": results,
            "remediation": remediation_items}
