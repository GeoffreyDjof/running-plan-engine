"""10k beginner 3× + advanced 4× planner gates."""

from __future__ import annotations

import json
from pathlib import Path

from plan_engine.models import Plan, PlanRequest
from plan_engine.planner import generate_plan
from plan_engine.validator import validate_plan

ROOT = Path(__file__).resolve().parents[1]


def _check(example: str, template_substr: str, peak_cap: float) -> None:
    path = ROOT / "examples" / example
    req = PlanRequest.model_validate_json(path.read_text())
    result = generate_plan(req)
    assert isinstance(result, Plan), result
    assert template_substr in result.meta.method
    payload = result.model_dump(mode="json")
    payload["_request"] = json.loads(path.read_text())
    vr = validate_plan(payload)
    assert vr.ok, [(e.code, e.rule_id, e.message) for e in vr.errors]
    load_kms = [
        round(sum(s.total_km or 0 for s in w.sessions), 1)
        for w in result.plan
        if not w.is_deload and w.phase.value not in ("taper", "race")
    ]
    assert max(load_kms) <= peak_cap


def test_generate_beginner_10k_validates() -> None:
    _check("beginner_10k.json", "beginner_10k_3x", 40.0)


def test_generate_advanced_10k_validates() -> None:
    _check("advanced_10k.json", "advanced_10k_4x", 80.0)


def test_beginner_no_quality_hard() -> None:
    req = PlanRequest.model_validate_json((ROOT / "examples" / "beginner_10k.json").read_text())
    plan = generate_plan(req)
    assert isinstance(plan, Plan)
    hard = {"intervals", "reps"}
    kinds = {s.kind.value for w in plan.plan for s in w.sessions}
    assert kinds.isdisjoint(hard)


def test_canonical_dumps_roundtrip() -> None:
    for name in ("beginner_10k", "advanced_10k", "intermediate_10k"):
        data = json.loads((ROOT / "examples" / f"{name}_plan_generated.json").read_text())
        Plan.model_validate(data)
        payload = dict(data)
        payload["_request"] = json.loads((ROOT / "examples" / f"{name}.json").read_text())
        vr = validate_plan(payload)
        assert vr.ok, (name, [(e.rule_id, e.message) for e in vr.errors])
