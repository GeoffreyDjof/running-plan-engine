"""VDOT + Daniels pace zones (Phase 1).

Method: Jack Daniels Running Formula regressions (VO2 / %VO2max), scaled to
match the published VDOT table anchor (5k in 20:00 → VDOT 51.0) per
``docs/coaching-rules.md`` §3.7 and ``VDOT_TABLE_SCALE``.

Training paces are derived as %VO2 of VDOT via ``ZONE_VO2_FRACTION``, stored
as integer seconds/km. Planner/templates must consume paces only from
``PaceZones`` — never free-text paces.
"""

from __future__ import annotations

import math
from typing import Literal

from plan_engine import constants as C
from plan_engine.models import (
    Benchmark,
    EngineError,
    ErrorCode,
    PaceRange,
    PaceZoneDetail,
    PaceZones,
)

DistanceKey = Literal["5k", "10k", "half", "marathon"]


def distance_key_from_km(distance_km: float, *, tol: float = 0.05) -> DistanceKey | None:
    """Map a kilometre distance to a canonical key, or None if unknown."""
    for km, key in C.DISTANCE_KM_TO_KEY.items():
        if abs(distance_km - km) <= tol:
            return key  # type: ignore[return-value]
    return None


def _distance_m(distance_km: float) -> float:
    key = distance_key_from_km(distance_km)
    if key is not None:
        return C.DISTANCE_KEY_TO_M[key]
    return distance_km * 1000.0


def _round_half_up(value: float) -> int:
    """Non-negative half-up rounding to int (avoids banker's rounding)."""
    return int(math.floor(value + 0.5))


def _vo2_at_velocity(velocity_m_per_min: float) -> float:
    """Daniels oxygen cost of running (ml/kg/min) from velocity (m/min)."""
    v = velocity_m_per_min
    return -4.60 + 0.182258 * v + 0.000104 * v * v


def _vo2max_fraction(time_min: float) -> float:
    """Fraction of VO2max sustainable for ``time_min`` minutes (Daniels)."""
    t = time_min
    return (
        0.8
        + 0.1894393 * math.exp(-0.012778 * t)
        + 0.2989558 * math.exp(-0.1932605 * t)
    )


def _velocity_at_vo2(target_vo2: float) -> float:
    """Invert Daniels VO2(v) quadratic → velocity m/min."""
    a = 0.000104
    b = 0.182258
    c = -(target_vo2 + 4.60)
    disc = b * b - 4.0 * a * c
    if disc < 0:
        raise ValueError("no real velocity for target VO2")
    return (-b + math.sqrt(disc)) / (2.0 * a)


def _raw_vdot(distance_m: float, time_sec: int) -> float:
    if time_sec <= 0 or distance_m <= 0:
        raise ValueError("distance_m and time_sec must be positive")
    velocity = distance_m / (time_sec / 60.0)
    return _vo2_at_velocity(velocity) / _vo2max_fraction(time_sec / 60.0)


def benchmark_implausible_error(
    distance_km: float,
    time_sec: int,
    *,
    distance_key: DistanceKey | None = None,
) -> EngineError | None:
    """Return EngineError if benchmark time is outside coaching bounds."""
    key = distance_key or distance_key_from_km(distance_km)
    if key is None:
        return EngineError(
            code=ErrorCode.BENCHMARK_IMPLAUSIBLE,
            message_fr=(
                f"Distance de benchmark non supportée ({distance_km} km). "
                "Utilisez 5, 10, 21.0975 ou 42.195 km."
            ),
            details={"distance_km": distance_km, "time_sec": time_sec},
        )
    lo, hi = C.BENCHMARK_BOUNDS_SEC[key]
    if time_sec < lo or time_sec > hi:
        return EngineError(
            code=ErrorCode.BENCHMARK_IMPLAUSIBLE,
            message_fr=(
                f"Temps de benchmark invraisemblable pour {key} "
                f"({time_sec}s ; bornes {lo}–{hi}s)."
            ),
            details={
                "distance_key": key,
                "distance_km": distance_km,
                "time_sec": time_sec,
                "min_sec": lo,
                "max_sec": hi,
                "rule_id": "BENCHMARK_IMPLAUSIBLE",
            },
        )
    return None


def vdot_from_benchmark(distance_km: float, time_sec: int) -> float:
    """Compute table-calibrated VDOT. Caller must check plausibility first."""
    distance_m = _distance_m(distance_km)
    return _raw_vdot(distance_m, time_sec) * C.VDOT_TABLE_SCALE


def pace_zones_from_vdot(vdot: float) -> PaceZones:
    """Derive E/M/T/I/R paces (sec/km) from VDOT via Daniels %VO2 points."""
    if vdot <= 0:
        raise ValueError("vdot must be positive")
    zones: dict[str, PaceZoneDetail] = {}
    for key in C.PACE_ZONES_REQUIRED:
        frac = C.ZONE_VO2_FRACTION[key]
        velocity = _velocity_at_vo2(vdot * frac)
        pace = _round_half_up(60_000.0 / velocity)
        if pace <= 0:
            raise ValueError(f"non-positive pace for zone {key}")
        zones[key] = PaceZoneDetail(
            pace_sec_per_km=pace,
            label=C.ZONE_LABELS[key],
            range=pace_range_for(key, pace),
        )
    result = PaceZones(**zones)
    _assert_zone_order(result)
    return result


def _round_to_step(value: float, step: int) -> int:
    """Nearest multiple of `step`, ties rounded up (deterministic)."""
    return _round_half_up(value / step) * step


def pace_range_for(zone: str, pace_sec_per_km: int) -> PaceRange:
    """§3.9 band: nearest-5 s bounds, widened only to contain the center."""
    fast_pct, slow_pct = C.PACE_RANGE_PCT[zone]
    step = C.PACE_RANGE_ROUND_SEC
    lo = _round_to_step(pace_sec_per_km * (1.0 - fast_pct), step)
    hi = _round_to_step(pace_sec_per_km * (1.0 + slow_pct), step)
    lo = min(lo, pace_sec_per_km)
    hi = max(hi, pace_sec_per_km)
    if lo >= hi:  # degenerate band: open it on the slow side only
        hi = lo + step
    return PaceRange(min_sec_per_km=lo, max_sec_per_km=hi)


def _assert_zone_order(zones: PaceZones) -> None:
    """Enforce E > M > T > I and I >= R (sec/km)."""
    if not (
        zones.E.pace_sec_per_km
        > zones.M.pace_sec_per_km
        > zones.T.pace_sec_per_km
        > zones.I.pace_sec_per_km
        and zones.I.pace_sec_per_km >= zones.R.pace_sec_per_km
    ):
        raise ValueError(
            "pace zone order violated: require E>M>T>I and I>=R (sec/km)"
        )


def compute_paces(distance_km: float, time_sec: int) -> PaceZones | EngineError:
    """Full Phase-1 path: plausibility → VDOT → PaceZones."""
    err = benchmark_implausible_error(distance_km, time_sec)
    if err is not None:
        return err
    vdot = vdot_from_benchmark(distance_km, time_sec)
    return pace_zones_from_vdot(vdot)


def compute_paces_from_benchmark(benchmark: Benchmark) -> PaceZones | EngineError:
    """Convenience wrapper for ``PlanRequest.benchmark``."""
    return compute_paces(benchmark.distance_km, benchmark.time_sec)


def paces_confidence(*, is_estimate: bool, benchmark_date_age_days: int | None) -> str:
    """Heuristic confidence for PlanMeta (deterministic)."""
    if is_estimate:
        return "low"
    if benchmark_date_age_days is None:
        return "medium"
    if benchmark_date_age_days <= 90:
        return "high"
    if benchmark_date_age_days <= 180:
        return "medium"
    return "low"
