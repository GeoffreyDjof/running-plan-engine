"""EngineValid phase-2 — fixture-driven validator tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plan_engine.validator import validate_plan

FIXTURES = Path(__file__).resolve().parent / "fixtures"

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
