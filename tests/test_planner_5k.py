"""5k beginner / intermediate / advanced planner gates."""

from __future__ import annotations

import json
from pathlib import Path

from plan_engine.models import Plan, PlanRequest
from plan_engine.planner import generate_plan
from plan_engine.validator import validate_plan

ROOT = Path(__file__).resolve().parents[1]

CASES = [
    ("beginner_5k.json", "beginner_5k_3x", 35.0),
    ("intermediate_5k.json", "intermediate_5k_4x", 50.0),
    ("advanced_5k.json", "advanced_5k_4x", 70.0),
]


def test_generate_5k_levels_validate() -> None:
    for example, tmpl, cap in CASES:
        path = ROOT / "examples" / example
        req = PlanRequest.model_validate_json(path.read_text())
        plan = generate_plan(req)
        assert isinstance(plan, Plan), (example, plan)
        assert tmpl in plan.meta.method
        assert plan.meta.weeks == 10
        payload = plan.model_dump(mode="json")
        payload["_request"] = json.loads(path.read_text())
        vr = validate_plan(payload)
        assert vr.ok, (example, [(e.rule_id, e.message) for e in vr.errors])
        peak = max(
            round(sum(s.total_km or 0 for s in w.sessions), 1)
            for w in plan.plan
            if not w.is_deload and w.phase.value not in ("taper", "race")
        )
        assert peak <= cap


def test_beginner_5k_no_quality_hard() -> None:
    req = PlanRequest.model_validate_json((ROOT / "examples" / "beginner_5k.json").read_text())
    plan = generate_plan(req)
    assert isinstance(plan, Plan)
    kinds = {s.kind.value for w in plan.plan for s in w.sessions}
    assert kinds.isdisjoint({"intervals", "reps"})


def test_5k_canonical_dumps() -> None:
    for stem, _, _ in CASES:
        name = stem.replace(".json", "")
        data = json.loads((ROOT / "examples" / f"{name}_plan_generated.json").read_text())
        Plan.model_validate(data)
        payload = dict(data)
        payload["_request"] = json.loads((ROOT / "examples" / f"{name}.json").read_text())
        assert validate_plan(payload).ok
