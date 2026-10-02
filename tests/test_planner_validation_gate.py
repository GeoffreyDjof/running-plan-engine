"""P0-3: generate_plan never returns a plan that fails validate_plan."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plan_engine import planner
from plan_engine.models import EngineError, ErrorCode, Plan, PlanRequest, SessionKind
from plan_engine.validator import validate_plan

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [
    "beginner_5k", "intermediate_5k", "advanced_5k",
    "beginner_10k", "intermediate_10k", "advanced_10k",
    "beginner_half", "intermediate_half", "advanced_half",
]


def _req(name: str) -> PlanRequest:
    return PlanRequest.model_validate_json((ROOT / "examples" / f"{name}.json").read_text())


@pytest.mark.parametrize("name", EXAMPLES)
def test_generated_plans_pass_validator_with_athlete(name: str) -> None:
    req = _req(name)
    plan = planner.generate_plan(req)
    assert isinstance(plan, Plan), plan
    payload = plan.model_dump(mode="json")
    payload["_request"] = req.model_dump(mode="json")
    assert validate_plan(payload).ok


def test_unsafe_assembled_plan_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tamper the raw plan (+60 % jump week 2) → VALIDATION_FAILED + rule_id."""
    req = _req("intermediate_10k")
    raw = planner._assemble_plan(req)
    assert isinstance(raw, Plan)
    week = raw.plan[1]
    for s in week.sessions:
        if s.total_km:
            s.total_km = round(s.total_km * 1.6, 1)
    monkeypatch.setattr(planner, "_assemble_plan", lambda _r: raw)

    out = planner.generate_plan(req)
    assert isinstance(out, EngineError)
    assert out.code == ErrorCode.VALIDATION_FAILED
    assert out.details["rule_id"]
    assert out.details["rule_id"] in out.details["broken_rules"]
    assert out.details["errors"]
    assert "validateur" in out.message_fr


def test_injury_quality_returns_injury_error() -> None:
    """Injured athlete + quality sessions in the raw plan → INJURY_BLOCKS_QUALITY."""
    data = json.loads((ROOT / "examples" / "edge_injury_quality_blocked.json").read_text())
    data["goal"]["race_date"] = "2027-01-17"
    req = PlanRequest.model_validate(data)
    raw = planner._assemble_plan(req)
    assert isinstance(raw, Plan), raw
    kinds = {s.kind for w in raw.plan for s in w.sessions}
    assert kinds & {SessionKind.intervals, SessionKind.tempo, SessionKind.reps}

    out = planner.generate_plan(req)
    assert isinstance(out, EngineError)
    assert out.code == ErrorCode.INJURY_BLOCKS_QUALITY
    assert out.details["rule_id"] == "R13"
    assert "R13" in out.details["broken_rules"]
    assert out.details["errors"]


def test_validation_gate_is_deterministic() -> None:
    req = _req("beginner_half")
    a = planner.generate_plan(req)
    b = planner.generate_plan(req)
    assert isinstance(a, Plan) and isinstance(b, Plan)
    assert a.model_dump(mode="json") == b.model_dump(mode="json")
