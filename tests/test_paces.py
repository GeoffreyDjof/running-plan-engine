"""Phase 1 VDOT / pace zone tests (coaching-rules §3.7)."""

from __future__ import annotations

import pytest

from plan_engine import constants as C
from plan_engine.models import EngineError, ErrorCode, PaceZones
from plan_engine.paces import (
    compute_paces,
    pace_zones_from_vdot,
    vdot_from_benchmark,
)


def test_vdot_5k_20_minutes_near_51() -> None:
    vdot = vdot_from_benchmark(5.0, C.VDOT_ANCHOR_TIME_SEC)
    assert abs(vdot - C.VDOT_ANCHOR_EXPECTED) <= C.VDOT_TOLERANCE_ABS


@pytest.mark.parametrize(
    "distance_km,time_sec",
    [
        (5.0, 749),
        (5.0, 3601),
        (10.0, 1559),
        (10.0, 7201),
        (21.0975, 3479),
        (21.0975, 14401),
        (42.195, 7499),
        (42.195, 28801),
    ],
)
def test_benchmark_implausible_bounds(distance_km: float, time_sec: int) -> None:
    result = compute_paces(distance_km, time_sec)
    assert isinstance(result, EngineError)
    assert result.code == ErrorCode.BENCHMARK_IMPLAUSIBLE


def test_compute_paces_anchor_zones() -> None:
    result = compute_paces(5.0, 1200)
    assert isinstance(result, PaceZones)
    assert result.E.pace_sec_per_km > result.M.pace_sec_per_km
    assert result.M.pace_sec_per_km > result.T.pace_sec_per_km
    assert result.T.pace_sec_per_km > result.I.pace_sec_per_km
    assert result.I.pace_sec_per_km >= result.R.pace_sec_per_km
    for z in (result.E, result.M, result.T, result.I, result.R):
        assert isinstance(z.pace_sec_per_km, int)
        assert z.pace_sec_per_km > 0


def test_same_input_same_output() -> None:
    a = compute_paces(5.0, 1200)
    b = compute_paces(5.0, 1200)
    assert a == b


def test_boundary_times_accepted() -> None:
    lo, hi = C.BENCHMARK_BOUNDS_SEC["5k"]
    assert isinstance(compute_paces(5.0, lo), PaceZones)
    assert isinstance(compute_paces(5.0, hi), PaceZones)


def test_pace_zones_from_vdot_order() -> None:
    zones = pace_zones_from_vdot(51.0)
    assert zones.E.pace_sec_per_km > zones.R.pace_sec_per_km
