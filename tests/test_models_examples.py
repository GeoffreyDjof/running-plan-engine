"""Phase 0: PlanRequest examples + ErrorCode surface."""

from __future__ import annotations

from pathlib import Path

import pytest

from plan_engine.models import (
    VALIDATOR_RULE_IDS,
    ErrorCode,
    PlanRequest,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

HANDOFF_CODES = {
    "INSUFFICIENT_AVAILABILITY",
    "GOAL_TOO_SOON",
    "VOLUME_TOO_LOW_FOR_GOAL",
    "BENCHMARK_IMPLAUSIBLE",
    "INJURY_BLOCKS_QUALITY",
    "VALIDATION_FAILED",
}


@pytest.mark.parametrize(
    "name",
    [
        "beginner_10k.json",
        "intermediate_half.json",
        "edge_injury_quality_blocked.json",
    ],
)
def test_example_validates_as_plan_request(name: str) -> None:
    raw = (EXAMPLES / name).read_text(encoding="utf-8")
    req = PlanRequest.model_validate_json(raw)
    assert req.options.units == "metric"
    assert req.options.language == "fr"
    assert len(req.athlete.availability) >= 1


def test_edge_injury_example_documents_injury_constraint() -> None:
    req = PlanRequest.model_validate_json(
        (EXAMPLES / "edge_injury_quality_blocked.json").read_text(encoding="utf-8")
    )
    assert req.athlete.constraints.injuries
    # Planner/validator later: INJURY_BLOCKS_QUALITY if intervals/reps scheduled.


def test_error_code_is_exactly_six_handoff_codes() -> None:
    values = {c.value for c in ErrorCode}
    assert values == HANDOFF_CODES
    assert len(ErrorCode) == 6


def test_validator_rule_ids_are_not_error_codes() -> None:
    error_values = {c.value for c in ErrorCode}
    assert VALIDATOR_RULE_IDS.isdisjoint(error_values)
    expected = {
        "QUALITY_BACK_TO_BACK",
        "LONG_RUN_OVER_CEILING",
        "VOLUME_JUMP_TOO_HIGH",
        "SESSION_OVER_MAX_MINUTES",
        "BEGINNER_AGGRESSIVE_REPS",
        "INSUFFICIENT_EASY_RATIO",
        "MISSING_TAPER",
    }
    assert VALIDATOR_RULE_IDS == expected
