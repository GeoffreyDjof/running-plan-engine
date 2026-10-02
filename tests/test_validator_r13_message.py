"""R13 (injury blocks quality): French message text only.

Logic, rule_id, error code and the raw ``kind`` / ``week_index`` details are
unchanged; only the human-readable message is French.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from plan_engine.labels import SESSION_KIND_FR, session_kind_fr
from plan_engine.models import EngineError, ErrorCode, PlanRequest
from plan_engine.planner import generate_plan
from plan_engine.validator import validate_plan

ROOT = Path(__file__).resolve().parents[1]
AS_OF = dt.date(2026, 9, 26)


def _expected(week: int, label: str) -> str:
    return (
        "Blessure en cours : pas de séance de qualité tant qu'elle est active "
        f"(semaine {week} : {label}). Reste en endurance facile et fais valider "
        "la reprise par un professionnel de santé."
    )


def _edge_injury() -> EngineError:
    raw = (ROOT / "examples" / "edge_injury_quality_blocked.json").read_text(encoding="utf-8")
    result = generate_plan(PlanRequest.model_validate_json(raw), as_of_date=AS_OF)
    assert isinstance(result, EngineError), result
    return result


def test_session_kind_fr_table() -> None:
    assert SESSION_KIND_FR == {
        "tempo": "allure seuil",
        "cruise_intervals": "fractionné au seuil",
        "intervals": "fractionné VMA",
        "reps": "répétitions rapides",
        "race_pace": "allure course",
    }


def test_session_kind_fr_falls_back_to_raw_kind() -> None:
    assert session_kind_fr("intervals") == "fractionné VMA"
    assert session_kind_fr("hill_sprints") == "hill_sprints"


def test_edge_injury_code_and_rule_unchanged() -> None:
    err = _edge_injury()
    assert err.code == ErrorCode.INJURY_BLOCKS_QUALITY
    assert err.details["rule_id"] == "R13"
    assert "R13" in err.details["broken_rules"]


def test_edge_injury_message_is_french_with_week_and_label() -> None:
    err = _edge_injury()
    # First R13 hit on edge_injury is the week-2 tempo session.
    assert _expected(2, "allure seuil") in err.message_fr
    assert "Injury" not in err.message_fr
    assert "(R13)" in err.message_fr


def test_edge_injury_details_keep_raw_kind_and_week() -> None:
    err = _edge_injury()
    r13 = [e for e in err.details["errors"] if e["rule_id"] == "R13"]
    assert r13
    assert r13[0]["details"] == {"rule_id": "R13", "week_index": 2, "kind": "tempo"}
    for e in r13:
        assert e["code"] == ErrorCode.INJURY_BLOCKS_QUALITY.value
        kind, week = e["details"]["kind"], e["details"]["week_index"]
        assert kind in SESSION_KIND_FR  # raw enum value, not the French label
        assert e["message"] == _expected(week, SESSION_KIND_FR[kind])


@pytest.mark.parametrize("kind", sorted(SESSION_KIND_FR))
def test_r13_message_for_each_blocked_kind(kind: str) -> None:
    fixture = json.loads(
        (ROOT / "tests" / "fixtures" / "unsafe_injury_intervals.json").read_text(encoding="utf-8")
    )
    for week in fixture["weeks"]:
        for session in week["sessions"]:
            if session.get("kind") == "intervals":
                session["kind"] = kind
    vr = validate_plan(fixture)
    r13 = [e for e in vr.errors if e.rule_id == "R13"]
    assert r13
    for e in r13:
        assert e.code == ErrorCode.INJURY_BLOCKS_QUALITY.value
        assert e.details["kind"] == kind
        assert e.message == _expected(e.details["week_index"], SESSION_KIND_FR[kind])
