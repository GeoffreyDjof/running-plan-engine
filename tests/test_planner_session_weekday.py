"""P0-12: every session's weekday label matches its calendar date."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plan_engine.models import Plan, PlanRequest
from plan_engine.planner import generate_plan

_ROOT = Path(__file__).resolve().parents[1] / "examples"
_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_INPUTS = sorted(
    p
    for p in [*_ROOT.glob("*.json"), *(_ROOT / "demo").glob("*.json")]
    if not p.name.endswith("_plan_generated.json")
)


@pytest.mark.parametrize("path", _INPUTS, ids=lambda p: p.stem)
def test_session_weekday_matches_date(path: Path) -> None:
    req = PlanRequest.model_validate(json.loads(path.read_text(encoding="utf-8")))
    result = generate_plan(req)
    if not isinstance(result, Plan):
        pytest.skip("profile refused by design")
    for week in result.plan:
        for s in week.sessions:
            assert s.weekday.value == _WEEKDAYS[s.date.weekday()], (s.id, s.date)
            assert s.id.split("-")[1] == s.weekday.value


def test_demo_1_preday_footing_is_saturday() -> None:
    path = _ROOT / "demo" / "demo_1_beginner_5k.json"
    req = PlanRequest.model_validate(json.loads(path.read_text(encoding="utf-8")))
    plan = generate_plan(req)
    assert isinstance(plan, Plan)
    pre = [s for s in plan.plan[-1].sessions if s.title == "Footing pré-course"]
    assert len(pre) == 1
    assert pre[0].date.isoformat() == "2026-12-12"
    assert pre[0].weekday.value == "sat"
