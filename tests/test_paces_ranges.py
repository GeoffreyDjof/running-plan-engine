"""P0-6: pace ranges per zone (DomainCoach coaching-rules §3.9)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plan_engine import constants as C
from plan_engine.models import Plan, PlanRequest
from plan_engine.paces import pace_range_for, pace_zones_from_vdot
from plan_engine.planner import generate_plan

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _mmss(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}"


def test_easy_vdot_35_matches_coaching_rules_example() -> None:
    band = pace_zones_from_vdot(35).E.range
    assert band is not None
    assert (_mmss(band.min_sec_per_km), _mmss(band.max_sec_per_km)) == ("7:00", "7:45")


def test_threshold_vdot_51_is_not_widened_on_fast_side() -> None:
    # §3.9: nearest-5 s rounding, NOT floor on min (would give 4:05).
    band = pace_zones_from_vdot(51).T.range
    assert band is not None
    assert (_mmss(band.min_sec_per_km), _mmss(band.max_sec_per_km)) == ("4:10", "4:15")


@pytest.mark.parametrize("vdot", [v / 2 for v in range(50, 161)])
def test_every_zone_band_is_valid_and_contains_center(vdot: float) -> None:
    zones = pace_zones_from_vdot(vdot)
    for key in C.PACE_ZONES_REQUIRED:
        d = getattr(zones, key)
        band = d.range
        assert band is not None
        assert band.min_sec_per_km < band.max_sec_per_km
        assert band.min_sec_per_km <= d.pace_sec_per_km <= band.max_sec_per_km
        # Slow side at least as wide as fast side ("au doute, plus lent").
        assert (band.max_sec_per_km - d.pace_sec_per_km) >= (
            d.pace_sec_per_km - band.min_sec_per_km
        ) - C.PACE_RANGE_ROUND_SEC


def test_bounds_are_multiples_of_5_unless_widened_to_center() -> None:
    for pace in range(180, 600):
        for key in C.PACE_ZONES_REQUIRED:
            band = pace_range_for(key, pace)
            for bound in (band.min_sec_per_km, band.max_sec_per_km):
                assert bound % C.PACE_RANGE_ROUND_SEC == 0 or bound == pace


def test_generated_plans_carry_ranges_and_are_deterministic() -> None:
    raw = (EXAMPLES / "beginner_10k.json").read_text(encoding="utf-8")
    a = generate_plan(PlanRequest.model_validate_json(raw))
    b = generate_plan(PlanRequest.model_validate(json.loads(raw)))
    assert isinstance(a, Plan) and isinstance(b, Plan)
    assert a.model_dump_json() == b.model_dump_json()
    for key in C.PACE_ZONES_REQUIRED:
        assert getattr(a.pace_zones, key).range is not None
