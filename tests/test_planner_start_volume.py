"""P0-4: start volume capped by real recent km; unreachable goals refused."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from plan_engine import constants as C
from plan_engine.models import EngineError, ErrorCode, Plan, PlanRequest
from plan_engine.planner import generate_plan, reference_weekly_km
from plan_engine.validator import validate_plan

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [
    "beginner_5k", "intermediate_5k", "advanced_5k",
    "beginner_10k", "intermediate_10k", "advanced_10k",
    "beginner_half", "intermediate_half", "advanced_half",
]


def _data(name: str, recent: list[float] | None = None) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((ROOT / "examples" / f"{name}.json").read_text())
    if recent is not None:
        data["athlete"]["recent_weekly_km"] = recent
    return data


def _week_km(plan: Plan, i: int) -> float:
    return round(sum(s.total_km or 0.0 for s in plan.plan[i].sessions), 1)


def test_reference_km_is_min_of_median4_and_max2() -> None:
    assert reference_weekly_km([11, 10, 12, 11]) == 11.0
    assert reference_weekly_km([40, 40, 22, 21]) == 22.0  # dropping volume
    assert reference_weekly_km([5, 30, 31, 32, 33]) == 31.5  # last 4 only
    assert reference_weekly_km([]) is None


@pytest.mark.parametrize("name", EXAMPLES)
def test_week1_le_ratio_times_ref_and_examples_still_valid(name: str) -> None:
    data = _data(name)
    plan = generate_plan(PlanRequest.model_validate(data))
    assert isinstance(plan, Plan), plan
    ref = reference_weekly_km(data["athlete"]["recent_weekly_km"])
    assert ref is not None
    assert _week_km(plan, 0) <= round(C.START_VOLUME_MAX_RATIO * ref, 1) + 1e-9
    payload = plan.model_dump(mode="json")
    payload["_request"] = data
    assert validate_plan(payload).ok


def test_11km_week_half_refused() -> None:
    """DoD: a runner at 11 km/week never gets a ~31 km (or 16 km) week 1 for a half."""
    out = generate_plan(PlanRequest.model_validate(_data("beginner_half", [11, 10, 12, 11])))
    assert isinstance(out, EngineError)
    assert out.code == ErrorCode.VOLUME_TOO_LOW_FOR_GOAL
    assert out.details["ref_weekly_km"] == 11.0
    assert out.details["min_recent_km"] == 15.0
    assert "km/sem" in out.message_fr


def test_11km_week_5k_beginner_accepted_with_capped_start() -> None:
    data = _data("beginner_5k", [11, 10, 12, 11])
    plan = generate_plan(PlanRequest.model_validate(data))
    assert isinstance(plan, Plan), plan
    assert _week_km(plan, 0) <= 12.1
    payload = plan.model_dump(mode="json")
    payload["_request"] = data
    assert validate_plan(payload).ok


def test_empty_recent_km_refused() -> None:
    out = generate_plan(PlanRequest.model_validate(_data("beginner_5k", [])))
    assert isinstance(out, EngineError)
    assert out.code == ErrorCode.VOLUME_TOO_LOW_FOR_GOAL


@pytest.mark.parametrize(
    ("name", "below", "at"),
    [
        ("beginner_5k", 9.5, 10.0),
        ("intermediate_10k", 19.5, 20.0),
        ("advanced_half", 28.5, 29.0),
    ],
)
def test_goal_thresholds_fail_below_pass_at(name: str, below: float, at: float) -> None:
    low = generate_plan(PlanRequest.model_validate(_data(name, [below] * 4)))
    assert isinstance(low, EngineError)
    assert low.code == ErrorCode.VOLUME_TOO_LOW_FOR_GOAL
    ok = generate_plan(PlanRequest.model_validate(_data(name, [at] * 4)))
    assert isinstance(ok, Plan), ok
    assert _week_km(ok, 0) <= round(C.START_VOLUME_MAX_RATIO * at, 1) + 1e-9


def test_volume_sweep_all_examples_pass_validator() -> None:
    """Every accepted recent volume 10..59 km/wk yields a validator-clean plan."""
    import json
    from pathlib import Path

    from plan_engine.models import PlanRequest
    from plan_engine.planner import generate_plan
    from plan_engine.validator import validate_plan

    for f in sorted(Path("examples").glob("*.json")):
        base = json.loads(f.read_text())
        if "athlete" not in base:
            continue
        for v in range(10, 60):
            d = json.loads(f.read_text())
            d["athlete"]["recent_weekly_km"] = [v] * 4
            p = generate_plan(PlanRequest.model_validate(d))
            if not hasattr(p, "plan"):
                continue
            pay = p.model_dump(mode="json")
            pay["_request"] = d
            r = validate_plan(pay)
            assert r.ok, (f.stem, v, [e.rule_id for e in r.errors])
