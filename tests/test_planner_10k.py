"""Phase 3: intermediate 10k planner + validator gate."""

from __future__ import annotations

import json
from pathlib import Path

from plan_engine.models import EngineError, Plan, PlanRequest
from plan_engine.planner import generate_plan
from plan_engine.validator import validate_plan

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "intermediate_10k.json"


def test_generate_intermediate_10k_validates() -> None:
    req = PlanRequest.model_validate_json(EXAMPLE.read_text())
    result = generate_plan(req)
    assert isinstance(result, Plan), result
    assert result.meta.weeks == 11
    assert len(result.plan) == 11
    assert result.pace_zones.E.pace_sec_per_km > result.pace_zones.R.pace_sec_per_km

    payload = result.model_dump(mode="json")
    payload["_request"] = json.loads(EXAMPLE.read_text())
    vr = validate_plan(payload)
    assert vr.ok, [(e.code, e.rule_id, e.message) for e in vr.errors]


def test_insufficient_availability() -> None:
    data = json.loads(EXAMPLE.read_text())
    data["athlete"]["availability"] = [
        {"weekday": "tue", "max_minutes": 60},
        {"weekday": "thu", "max_minutes": 60},
    ]
    data["options"]["sessions_per_week"] = 4
    req = PlanRequest.model_validate(data)
    result = generate_plan(req)
    assert isinstance(result, EngineError)
    assert result.code.value == "INSUFFICIENT_AVAILABILITY"


def test_generated_artifact_is_canonical_plan() -> None:
    """Review dump must round-trip Plan.model_validate (EngineValid veto)."""
    path = ROOT / "examples" / "intermediate_10k_plan_generated.json"
    data = json.loads(path.read_text())
    plan = Plan.model_validate(data)
    assert plan.plan[0].sessions[0].total_km is not None
    assert plan.plan[0].sessions[0].total_km > 0
    assert plan.pace_zones.E.pace_sec_per_km > 0
    payload = dict(data)
    payload["_request"] = json.loads(EXAMPLE.read_text())
    vr = validate_plan(payload)
    assert vr.ok, [(e.rule_id, e.message) for e in vr.errors]
