"""Half marathon beginner / intermediate / advanced planner gates."""

from __future__ import annotations

import json
from pathlib import Path

from plan_engine.models import Plan, PlanRequest
from plan_engine.planner import generate_plan
from plan_engine.validator import validate_plan

ROOT = Path(__file__).resolve().parents[1]

CASES = [
    ("beginner_half.json", "beginner_half_3x", 45.0),
    ("intermediate_half.json", "intermediate_half_4x", 65.0),
    ("advanced_half.json", "advanced_half_4x", 90.0),
]


def test_generate_half_levels_validate() -> None:
    for example, tmpl, cap in CASES:
        path = ROOT / "examples" / example
        req = PlanRequest.model_validate_json(path.read_text())
        plan = generate_plan(req)
        assert isinstance(plan, Plan), (example, plan)
        assert tmpl in plan.meta.method
        assert plan.meta.weeks == 12
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


def test_half_taper_window_10_to_14_days() -> None:
    req = PlanRequest.model_validate_json(
        (ROOT / "examples" / "intermediate_half.json").read_text()
    )
    plan = generate_plan(req)
    assert isinstance(plan, Plan)
    race = next(
        s.date
        for w in plan.plan
        for s in w.sessions
        if w.phase.value == "race" and s.kind.value == "race_pace"
    )
    taper_dates = [s.date for w in plan.plan if w.phase.value == "taper" for s in w.sessions]
    assert taper_dates
    span = (race - min(taper_dates)).days
    assert 10 <= span <= 14


def test_half_canonical_dumps() -> None:
    for stem, _, _ in CASES:
        name = stem.replace(".json", "")
        data = json.loads((ROOT / "examples" / f"{name}_plan_generated.json").read_text())
        Plan.model_validate(data)
        payload = dict(data)
        payload["_request"] = json.loads((ROOT / "examples" / f"{name}.json").read_text())
        assert validate_plan(payload).ok
