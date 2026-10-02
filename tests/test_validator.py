"""EngineValid phase-2 — fixture-driven validator tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plan_engine.validator import reference_weekly_km, validate_plan

FIXTURES = Path(__file__).resolve().parent / "fixtures"
EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

# Fixture → expected top-level ErrorCode (handoff 6 codes only).
# Most safety rules emit VALIDATION_FAILED with details.rule_id.
UNSAFE_CASES: list[tuple[str, str, str]] = [
    # fixture stem, expected code, rule_id
    ("unsafe_quality_back_to_back", "VALIDATION_FAILED", "QUALITY_BACK_TO_BACK"),
    ("unsafe_long_run_share", "VALIDATION_FAILED", "LONG_RUN_OVER_CEILING"),
    ("unsafe_weekly_jump", "VALIDATION_FAILED", "VOLUME_JUMP_TOO_HIGH"),
    ("unsafe_session_over_max_minutes", "VALIDATION_FAILED", "SESSION_OVER_MAX_MINUTES"),
    ("unsafe_beginner_reps", "VALIDATION_FAILED", "BEGINNER_AGGRESSIVE_REPS"),
    ("unsafe_injury_intervals", "INJURY_BLOCKS_QUALITY", "R13"),
    ("unsafe_easy_share_low", "VALIDATION_FAILED", "INSUFFICIENT_EASY_RATIO"),
    ("unsafe_missing_taper", "VALIDATION_FAILED", "MISSING_TAPER"),
    ("unsafe_day_after_long", "VALIDATION_FAILED", "R09"),
    ("unsafe_two_hard_qualities", "VALIDATION_FAILED", "R06"),
    ("unsafe_peak_volume", "VALIDATION_FAILED", "R15"),
    ("unsafe_consecutive_large_increases", "VALIDATION_FAILED", "R02"),
    ("unsafe_no_deload", "VALIDATION_FAILED", "R03"),
    ("unsafe_deload_fraction", "VALIDATION_FAILED", "R04"),
    ("unsafe_benchmark_implausible", "BENCHMARK_IMPLAUSIBLE", "R17"),
    ("unsafe_start_volume_above_recent", "VALIDATION_FAILED", "START_VOLUME_ABOVE_RECENT"),
]


def _load(name: str) -> dict:
    path = FIXTURES / name
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def test_valid_plan_passes():
    plan = _load("valid_plan.json")
    result = validate_plan(plan)
    assert result.ok is True, [e.model_dump() for e in result.errors]
    assert result.errors == []


@pytest.mark.parametrize(
    "stem,expected_code,rule_id",
    UNSAFE_CASES,
    ids=[c[0] for c in UNSAFE_CASES],
)
def test_unsafe_fixture_fails_with_expected_code(stem: str, expected_code: str, rule_id: str):
    plan = _load(f"{stem}.json")
    result = validate_plan(plan)
    assert result.ok is False, f"{stem} unexpectedly passed"
    codes = [e.code for e in result.errors]
    assert expected_code in codes, (
        f"{stem}: expected code {expected_code} in {codes}; "
        f"errors={[e.model_dump() for e in result.errors]}"
    )
    matching = [e for e in result.errors if e.code == expected_code]
    rule_ids = {e.rule_id for e in matching} | {
        (e.details or {}).get("rule_id") for e in matching
    }
    assert rule_id in rule_ids, (
        f"{stem}: expected rule_id {rule_id} on {expected_code} errors; "
        f"got {rule_ids}; errors={[e.model_dump() for e in result.errors]}"
    )


# ---------------------------------------------------------------------------
# P0-5 / R21 START_VOLUME_ABOVE_RECENT (DomainCoach P0-1 §3.8)
# ---------------------------------------------------------------------------
_START_RULE = "START_VOLUME_ABOVE_RECENT"


def _rule_ids(result) -> set[str | None]:
    return {e.rule_id for e in result.errors}


def _start_volume_plan(week1_km: float, recent: list[float]) -> dict:
    """Unsafe fixture rescaled so week 1 sums to exactly week1_km."""
    plan = _load("unsafe_start_volume_above_recent.json")
    plan["athlete"]["recent_weekly_km"] = recent
    factor = week1_km / 31.0
    for w in plan["weeks"]:
        for s in w["sessions"]:
            s["distance_km"] = round(s["distance_km"] * factor, 1)
            s["total_minutes_est"] = round(s["total_minutes_est"] * factor, 1)
    w1 = plan["weeks"][0]["sessions"]
    w1[-1]["distance_km"] = round(week1_km - sum(s["distance_km"] for s in w1[:-1]), 1)
    return plan


@pytest.mark.parametrize(
    "recent,expected",
    [
        ([11, 10, 12, 11], 11.0),  # median 11, max(last 2) 12 -> 11
        ([30, 28, 25, 22], 25.0),  # dropping volume: max(last 2) wins
        ([40, 50, 60, 70, 20, 22], 22.0),  # only last 4 weeks count
        ([15], 15.0),
        ([], None),
    ],
)
def test_reference_weekly_km(recent: list[float], expected: float | None) -> None:
    assert reference_weekly_km(recent) == expected


def test_start_volume_unsafe_fixture_details() -> None:
    result = validate_plan(_load("unsafe_start_volume_above_recent.json"))
    assert _rule_ids(result) == {_START_RULE}, [e.model_dump() for e in result.errors]
    (err,) = result.errors
    assert err.code == "VALIDATION_FAILED"
    d = err.details or {}
    assert d["rule_id"] == _START_RULE
    assert d["rule_ref"] == "R21"
    assert d["week_km"] == pytest.approx(31.0)
    assert d["ref_km"] == pytest.approx(11.0)
    assert d["max_km"] == pytest.approx(12.1)
    assert d["ratio"] == pytest.approx(31.0 / 11.0, abs=1e-3)


def test_start_volume_exactly_at_limit_passes() -> None:
    plan = _start_volume_plan(12.1, [11, 10, 12, 11])
    assert sum(s["distance_km"] for s in plan["weeks"][0]["sessions"]) == pytest.approx(12.1)
    result = validate_plan(plan)
    assert result.ok is True, [e.model_dump() for e in result.errors]


def test_start_volume_just_above_limit_fails() -> None:
    plan = _start_volume_plan(12.2, [11, 10, 12, 11])
    result = validate_plan(plan)
    assert _START_RULE in _rule_ids(result), [e.model_dump() for e in result.errors]


def test_start_volume_skipped_without_recent_km() -> None:
    plan = _load("unsafe_start_volume_above_recent.json")
    plan["athlete"]["recent_weekly_km"] = []
    result = validate_plan(plan)
    assert result.ok is True, [e.model_dump() for e in result.errors]


@pytest.mark.parametrize(
    "name",
    sorted(
        p.name.removesuffix("_plan_generated.json")
        for p in EXAMPLES.glob("*_plan_generated.json")
    ),
)
def test_generated_examples_pass_with_request_context(name: str) -> None:
    plan = json.loads((EXAMPLES / f"{name}_plan_generated.json").read_text(encoding="utf-8"))
    request = json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
    assert request["athlete"]["recent_weekly_km"], name
    plan["_request"] = request
    result = validate_plan(plan)
    assert result.ok is True, [e.model_dump() for e in result.errors]
