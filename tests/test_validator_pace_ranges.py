"""R22 PACE_RANGE_INVALID — pace bands per zone (ADR-007, coaching-rules §3.9)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plan_engine.models import PlanRequest
from plan_engine.paces import pace_zones_from_vdot
from plan_engine.planner import generate_plan
from plan_engine.validator import validate_plan

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
EXAMPLES = ROOT / "examples"
EXAMPLE_NAMES = sorted(
    p.name.removesuffix("_plan_generated.json") for p in EXAMPLES.glob("*_plan_generated.json")
)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _r22(result) -> list:
    return [e for e in result.errors if e.rule_id == "R22"]


def _with_zones(vdot: float) -> dict:
    plan = _load("valid_plan.json")
    plan["pace_zones"] = pace_zones_from_vdot(vdot).model_dump(mode="json")
    return plan


def test_unsafe_fixture_triggers_only_r22() -> None:
    result = validate_plan(_load("unsafe_pace_range_invalid.json"))
    assert result.ok is False
    assert {e.rule_id for e in result.errors} == {"R22"}, [e.model_dump() for e in result.errors]
    (err,) = result.errors
    assert err.code == "VALIDATION_FAILED"
    assert err.details is not None
    assert err.details["rule_id"] == "R22"
    assert err.details["rule_name"] == "PACE_RANGE_INVALID"
    assert err.details["check"] == "CENTER_OUTSIDE_RANGE"
    assert err.details["zone"] == "T"
    assert err.message.startswith("Zone T : allure centrale 5:10 /km hors de la fourchette")


def test_valid_plan_with_engine_ranges_passes() -> None:
    result = validate_plan(_with_zones(39.0))
    assert result.ok is True, [e.model_dump() for e in result.errors]


def test_range_absent_is_skipped() -> None:
    plan = _with_zones(51.0)
    for zone in plan["pace_zones"].values():
        zone["range"] = None
    assert validate_plan(plan).ok is True
    plan = _load("unsafe_pace_range_invalid.json")
    plan["pace_zones"]["T"]["range"] = None
    assert validate_plan(plan).ok is True


@pytest.mark.parametrize(
    "zone,band,check",
    [
        ("T", (255, 250), "MIN_NOT_BELOW_MAX"),
        ("T", (250, 250), "MIN_NOT_BELOW_MAX"),
        ("E", (330, 340), "CENTER_OUTSIDE_RANGE"),
        ("I", (225, 260), "ADJACENT_ZONES_OVERLAP"),  # I.max 4:20 > T.min 4:10
        ("M", (245, 275), "ADJACENT_ZONES_OVERLAP"),  # T.max 4:15 > M.min 4:05
    ],
)
def test_each_r22_check_fails(zone: str, band: tuple[int, int], check: str) -> None:
    plan = _with_zones(51.0)  # E 5:10–5:45, M 4:25–4:35, T 4:10–4:15, I 3:50–3:55
    plan["pace_zones"][zone]["range"] = {"min_sec_per_km": band[0], "max_sec_per_km": band[1]}
    errs = _r22(validate_plan(plan))
    assert check in {(e.details or {}).get("check") for e in errs}, [e.model_dump() for e in errs]


def test_adjacent_bands_touching_is_allowed() -> None:
    plan = _with_zones(51.0)
    t_min = plan["pace_zones"]["T"]["range"]["min_sec_per_km"]
    plan["pace_zones"]["I"]["range"]["max_sec_per_km"] = t_min
    assert _r22(validate_plan(plan)) == []


@pytest.mark.parametrize("vdot", [v / 2 for v in range(60, 141)])
def test_engine_ranges_pass_r22_vdot_30_to_70(vdot: float) -> None:
    assert _r22(validate_plan(_with_zones(vdot))) == []


@pytest.mark.parametrize("name", EXAMPLE_NAMES)
def test_committed_generated_examples_still_pass(name: str) -> None:
    plan = json.loads((EXAMPLES / f"{name}_plan_generated.json").read_text(encoding="utf-8"))
    plan["_request"] = json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
    result = validate_plan(plan)
    assert result.ok is True, [e.model_dump() for e in result.errors]


@pytest.mark.parametrize("name", EXAMPLE_NAMES)
def test_freshly_generated_plans_with_ranges_pass(name: str) -> None:
    raw = (EXAMPLES / f"{name}.json").read_text(encoding="utf-8")
    plan = generate_plan(PlanRequest.model_validate_json(raw))
    payload = plan.model_dump(mode="json")
    assert payload["pace_zones"]["E"]["range"] is not None
    payload["_request"] = json.loads(raw)
    result = validate_plan(payload)
    assert result.ok is True, [e.model_dump() for e in result.errors]
