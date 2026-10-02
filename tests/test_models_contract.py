"""P0-2 contract: PaceRange, as_of_date, structured PlanWarning."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from plan_engine.models import (
    EngineError,
    ErrorCode,
    Options,
    PaceRange,
    PaceZoneDetail,
    Plan,
    PlanMeta,
    PlanRequest,
    PlanWarning,
)
from plan_engine.planner import generate_plan

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
_GENERATED_AT = dt.datetime(2026, 9, 26, 9, 0, 0, tzinfo=dt.UTC)


def _input_example_names() -> list[str]:
    return sorted(
        p.name
        for p in EXAMPLES.glob("*.json")
        if not p.name.endswith("_plan_generated.json")
    )


def test_pace_range_rejects_min_not_strictly_less_than_max() -> None:
    with pytest.raises(ValidationError):
        PaceRange(min_sec_per_km=400, max_sec_per_km=300)
    with pytest.raises(ValidationError):
        PaceRange(min_sec_per_km=300, max_sec_per_km=300)


def test_pace_range_rejects_non_positive() -> None:
    with pytest.raises(ValidationError):
        PaceRange(min_sec_per_km=0, max_sec_per_km=300)
    with pytest.raises(ValidationError):
        PaceRange(min_sec_per_km=-10, max_sec_per_km=300)
    with pytest.raises(ValidationError):
        PaceRange(min_sec_per_km=200, max_sec_per_km=0)


def test_pace_range_accepts_min_faster_than_max() -> None:
    band = PaceRange(min_sec_per_km=300, max_sec_per_km=345)
    assert band.min_sec_per_km == 300
    assert band.max_sec_per_km == 345


def test_pace_zone_detail_range_is_optional() -> None:
    zone = PaceZoneDetail(pace_sec_per_km=420, label="Easy")
    assert zone.range is None


def test_pace_zone_detail_center_must_sit_inside_range() -> None:
    band = PaceRange(min_sec_per_km=400, max_sec_per_km=465)
    PaceZoneDetail(pace_sec_per_km=400, label="Easy", range=band)
    PaceZoneDetail(pace_sec_per_km=420, label="Easy", range=band)
    PaceZoneDetail(pace_sec_per_km=465, label="Easy", range=band)
    with pytest.raises(ValidationError):
        PaceZoneDetail(pace_sec_per_km=399, label="Easy", range=band)
    with pytest.raises(ValidationError):
        PaceZoneDetail(pace_sec_per_km=466, label="Easy", range=band)


def test_as_of_date_parses_on_options() -> None:
    options = Options.model_validate(
        {
            "sessions_per_week": 4,
            "include_strength": False,
            "units": "metric",
            "language": "fr",
            "as_of_date": "2026-10-02",
        }
    )
    assert options.as_of_date == dt.date(2026, 10, 2)


def test_as_of_date_defaults_to_none_and_round_trips_on_request() -> None:
    raw = json.loads((EXAMPLES / "beginner_10k.json").read_text(encoding="utf-8"))
    req = PlanRequest.model_validate(raw)
    assert req.options.as_of_date is None

    raw["options"]["as_of_date"] = "2026-09-26"
    req = PlanRequest.model_validate(raw)
    assert req.options.as_of_date == dt.date(2026, 9, 26)
    dumped = req.model_dump(mode="json")
    assert dumped["options"]["as_of_date"] == "2026-09-26"


def test_plan_meta_can_carry_as_of_date() -> None:
    meta = PlanMeta(
        engine_version="0.1.0",
        generated_at=_GENERATED_AT,
        vdot=35.0,
        paces_confidence="low",
        start_date=dt.date(2026, 9, 28),
        weeks=11,
        as_of_date=dt.date(2026, 9, 26),
    )
    assert meta.as_of_date == dt.date(2026, 9, 26)
    assert meta.warnings == []


def test_plan_warning_shape_and_default_empty() -> None:
    warning = PlanWarning(
        code="START_VOLUME_CAPPED",
        message_fr="Volume de départ plafonné.",
        details={"capped_km": 32},
    )
    assert warning.code == "START_VOLUME_CAPPED"
    assert warning.message_fr
    assert warning.details["capped_km"] == 32

    bare = PlanWarning(code="START_VOLUME_CAPPED", message_fr="Volume de départ plafonné.")
    assert bare.details == {}

    meta = PlanMeta(
        engine_version="0.1.0",
        generated_at=_GENERATED_AT,
        vdot=35.0,
        paces_confidence="low",
        start_date=dt.date(2026, 9, 28),
        weeks=11,
    )
    assert meta.warnings == []

    meta = PlanMeta(
        engine_version="0.1.0",
        generated_at=_GENERATED_AT,
        vdot=35.0,
        paces_confidence="low",
        start_date=dt.date(2026, 9, 28),
        weeks=11,
        warnings=[warning],
    )
    assert meta.warnings[0].code == "START_VOLUME_CAPPED"


def test_plan_meta_rejects_legacy_string_warnings() -> None:
    with pytest.raises(ValidationError):
        PlanMeta(
            engine_version="0.1.0",
            generated_at=_GENERATED_AT,
            vdot=35.0,
            paces_confidence="low",
            start_date=dt.date(2026, 9, 28),
            weeks=11,
            warnings=["legacy string warning"],
        )


@pytest.mark.parametrize("name", _input_example_names())
def test_every_committed_example_input_parses(name: str) -> None:
    raw = (EXAMPLES / name).read_text(encoding="utf-8")
    req = PlanRequest.model_validate_json(raw)
    assert req.options.units == "metric"
    assert req.options.language == "fr"


@pytest.mark.parametrize(
    "name",
    sorted(p.name for p in EXAMPLES.glob("*_plan_generated.json")),
)
def test_generated_plan_examples_still_validate(name: str) -> None:
    Plan.model_validate_json((EXAMPLES / name).read_text(encoding="utf-8"))


def test_edge_injury_example_reaches_injury_path() -> None:
    """Since P0-3 the validator gate runs inside generate_plan: the injury
    example is refused with a typed INJURY_BLOCKS_QUALITY / R13 error."""
    raw = (EXAMPLES / "edge_injury_quality_blocked.json").read_text(encoding="utf-8")
    req = PlanRequest.model_validate_json(raw)
    assert req.goal.race_date == dt.date(2027, 1, 17)
    result = generate_plan(req)
    assert isinstance(result, EngineError)
    assert result.code == ErrorCode.INJURY_BLOCKS_QUALITY
    assert "R13" in set(result.details.get("broken_rules", []))
