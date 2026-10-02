"""Plan safety validator (EngineValid phase-2).

Prefer plan_engine.models when available (ArchiPlan owns EngineError / Plan /
Session / ErrorCode). Validation fixtures use a flat EngineValid shape
(athlete/goal/weeks); ArchiPlan Plan is nested (meta/pace_zones/plan). This
module normalizes both into a private view — do not force fixtures through
ArchiPlan Plan.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from plan_engine import constants as C

# ---------------------------------------------------------------------------
# Prefer ArchiPlan ErrorCode / EngineError
# ---------------------------------------------------------------------------
try:
    from plan_engine.models import ErrorCode, EngineError as ArchiEngineError
except ImportError:  # pragma: no cover — models may lag behind
    from enum import Enum

    class ErrorCode(str, Enum):  # type: ignore[no-redef]
        INSUFFICIENT_AVAILABILITY = "INSUFFICIENT_AVAILABILITY"
        GOAL_TOO_SOON = "GOAL_TOO_SOON"
        VOLUME_TOO_LOW_FOR_GOAL = "VOLUME_TOO_LOW_FOR_GOAL"
        BENCHMARK_IMPLAUSIBLE = "BENCHMARK_IMPLAUSIBLE"
        INJURY_BLOCKS_QUALITY = "INJURY_BLOCKS_QUALITY"
        VALIDATION_FAILED = "VALIDATION_FAILED"

    ArchiEngineError = None  # type: ignore[assignment, misc]


def _code(c: Any) -> str:
    return c.value if hasattr(c, "value") else str(c)


# ---------------------------------------------------------------------------
# Private plan view (fixture-compatible; ArchiPlan may replace later)
# ---------------------------------------------------------------------------
class InjuryInfo(BaseModel):
    model_config = ConfigDict(extra="allow")
    active: bool = False


class AthleteInfo(BaseModel):
    model_config = ConfigDict(extra="allow")
    level: str = "intermediate"
    injury: InjuryInfo = Field(default_factory=InjuryInfo)


class GoalInfo(BaseModel):
    model_config = ConfigDict(extra="allow")
    distance: str = "10k"
    race_date: str | None = None


class BenchmarkInfo(BaseModel):
    model_config = ConfigDict(extra="allow")
    distance: str = "5k"
    time_seconds: int | None = None


class DayAvailability(BaseModel):
    model_config = ConfigDict(extra="allow")
    max_minutes: int | None = None


class AvailabilityInfo(BaseModel):
    model_config = ConfigDict(extra="allow")
    sessions_per_week: int | None = None
    days: dict[str, DayAvailability] = Field(default_factory=dict)


class SessionView(BaseModel):
    model_config = ConfigDict(extra="allow")
    date: str | None = None
    weekday: str | None = None
    kind: str = "easy"
    distance_km: float = 0.0
    total_minutes_est: float | None = None


class WeekView(BaseModel):
    model_config = ConfigDict(extra="allow")
    week_index: int
    phase: str = "base"
    is_deload: bool = False
    sessions: list[SessionView] = Field(default_factory=list)


class PaceZoneView(BaseModel):
    """One pace zone: central pace + optional inclusive band (ADR-007)."""

    model_config = ConfigDict(extra="allow")
    pace_sec_per_km: float | None = None
    range_min: float | None = None
    range_max: float | None = None


class PlanView(BaseModel):
    """Flat validation view — matches EngineValid fixtures."""

    model_config = ConfigDict(extra="allow")
    athlete: AthleteInfo = Field(default_factory=AthleteInfo)
    goal: GoalInfo = Field(default_factory=GoalInfo)
    benchmark: BenchmarkInfo | None = None
    availability: AvailabilityInfo = Field(default_factory=AvailabilityInfo)
    weeks: list[WeekView] = Field(default_factory=list)
    warnings: list[Any] = Field(default_factory=list)
    pace_zones: dict[str, PaceZoneView] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public result API
# ---------------------------------------------------------------------------
class ValidationError(BaseModel):
    code: str
    message: str
    rule_id: str | None = None
    details: dict[str, Any] | None = None


class ValidationResult(BaseModel):
    ok: bool
    errors: list[ValidationError] = Field(default_factory=list)


class EngineError(Exception):
    """Exception wrapper; mirrors ArchiPlan EngineError fields when raising."""

    def __init__(
        self,
        code: str,
        message: str = "",
        message_fr: str | None = None,
        details: dict[str, Any] | None = None,
        blocking: bool = True,
        rule_id: str | None = None,
    ) -> None:
        self.code = code
        self.message = message or (message_fr or "")
        self.message_fr = message_fr or message
        self.details = dict(details or {})
        if rule_id is not None:
            self.details.setdefault("rule_id", rule_id)
        self.blocking = blocking
        self.rule_id = rule_id
        super().__init__(self.message)

    def to_archi(self) -> Any:
        if ArchiEngineError is None:
            return self
        return ArchiEngineError(
            code=ErrorCode(self.code),
            message_fr=self.message_fr,
            details=self.details,
        )


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------
_KM_TO_LABEL = {
    5.0: "5k",
    10.0: "10k",
    21.0975: "half",
    21.1: "half",
    42.195: "marathon",
    42.2: "marathon",
}
_LABEL_TO_KM = {"5k": 5.0, "10k": 10.0, "half": 21.0975, "marathon": 42.195}


def _distance_label(value: Any) -> str:
    if value is None:
        return "10k"
    if isinstance(value, str):
        key = value.strip().lower()
        if key in _LABEL_TO_KM:
            return key
        try:
            return _distance_label(float(key))
        except ValueError:
            return key
    try:
        km = float(value)
    except (TypeError, ValueError):
        return "10k"
    if km in _KM_TO_LABEL:
        return _KM_TO_LABEL[km]
    for ref, label in _KM_TO_LABEL.items():
        if abs(km - ref) < 0.2:
            return label
    return "10k"


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------
_WEEKDAY_ORDER = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _dump(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="python")
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return obj


def _normalize_availability(raw: Any) -> AvailabilityInfo:
    if raw is None:
        return AvailabilityInfo()
    data = _dump(raw)
    if isinstance(data, list):
        days: dict[str, DayAvailability] = {}
        for item in data:
            item = _dump(item)
            wd = str(item.get("weekday", "")).lower()[:3]
            if wd:
                days[wd] = DayAvailability(max_minutes=item.get("max_minutes"))
        return AvailabilityInfo(days=days)
    if isinstance(data, dict):
        if "days" in data and isinstance(data["days"], dict):
            days = {
                str(k).lower()[:3]: DayAvailability.model_validate(_dump(v))
                for k, v in data["days"].items()
            }
            return AvailabilityInfo(
                sessions_per_week=data.get("sessions_per_week"),
                days=days,
            )
        # dict of weekday -> {max_minutes}
        if all(isinstance(v, (dict, DayAvailability)) for v in data.values()):
            days = {
                str(k).lower()[:3]: DayAvailability.model_validate(_dump(v))
                for k, v in data.items()
                if str(k).lower()[:3] in _WEEKDAY_ORDER
            }
            if days:
                return AvailabilityInfo(days=days)
    return AvailabilityInfo()


def _normalize_pace_zones(raw: Any) -> dict[str, PaceZoneView]:
    """{E: {pace_sec_per_km, range: {min_sec_per_km, max_sec_per_km} | None}, ...}."""
    data = _dump(raw) if raw is not None else None
    if not isinstance(data, dict):
        return {}
    zones: dict[str, PaceZoneView] = {}
    for key, value in data.items():
        zone = _dump(value)
        if not isinstance(zone, dict):
            continue
        band = _dump(zone.get("range")) if zone.get("range") is not None else None
        zones[str(key).upper()] = PaceZoneView(
            pace_sec_per_km=zone.get("pace_sec_per_km"),
            range_min=band.get("min_sec_per_km") if isinstance(band, dict) else None,
            range_max=band.get("max_sec_per_km") if isinstance(band, dict) else None,
        )
    return zones


def _injury_active(athlete: dict[str, Any]) -> bool:
    inj = athlete.get("injury")
    if isinstance(inj, dict) and "active" in inj:
        return bool(inj["active"])
    if hasattr(inj, "active"):
        return bool(inj.active)
    constraints = athlete.get("constraints") or {}
    constraints = _dump(constraints)
    injuries = constraints.get("injuries") if isinstance(constraints, dict) else None
    if injuries:
        return True
    return False


def _session_from_raw(raw: Any) -> SessionView:
    data = _dump(raw)
    kind = data.get("kind", "easy")
    if hasattr(kind, "value"):
        kind = kind.value
    dist = data.get("distance_km")
    if dist is None:
        dist = data.get("total_km") or 0.0
    d = data.get("date")
    if isinstance(d, date):
        d = d.isoformat()
    wd = data.get("weekday")
    if hasattr(wd, "value"):
        wd = wd.value
    return SessionView(
        date=d,
        weekday=wd,
        kind=str(kind),
        distance_km=float(dist or 0.0),
        total_minutes_est=data.get("total_minutes_est"),
    )


def _week_from_raw(raw: Any) -> WeekView:
    data = _dump(raw)
    phase = data.get("phase", "base")
    if hasattr(phase, "value"):
        phase = phase.value
    return WeekView(
        week_index=int(data["week_index"]),
        phase=str(phase),
        is_deload=bool(data.get("is_deload", False)),
        sessions=[_session_from_raw(s) for s in data.get("sessions") or []],
    )


def _coerce_plan(plan: Any) -> PlanView:
    """Accept flat fixture dict, PlanView, or ArchiPlan Plan (+ optional context)."""
    data = _dump(plan)

    # ArchiPlan nested Plan: {meta, pace_zones, plan: [...]}
    if (
        isinstance(data, dict)
        and "plan" in data
        and isinstance(data.get("plan"), list)
        and "weeks" not in data
    ):
        weeks = [_week_from_raw(w) for w in data["plan"]]
        # Context may be attached under _request / request / input
        ctx = data.get("_request") or data.get("request") or data.get("input") or {}
        ctx = _dump(ctx) if ctx else {}
        athlete_raw = _dump(ctx.get("athlete") or data.get("athlete") or {})
        goal_raw = _dump(ctx.get("goal") or data.get("goal") or {})
        bm_raw = ctx.get("benchmark") or data.get("benchmark")
        options = _dump(ctx.get("options") or {})
        avail_src = None
        if athlete_raw:
            avail_src = athlete_raw.get("availability")
        if avail_src is None:
            avail_src = data.get("availability")
        level = "intermediate"
        if athlete_raw.get("level"):
            lv = athlete_raw["level"]
            level = lv.value if hasattr(lv, "value") else str(lv)
        goal_distance = _distance_label(goal_raw.get("distance") or goal_raw.get("distance_km"))
        race_date = goal_raw.get("race_date")
        if isinstance(race_date, date):
            race_date = race_date.isoformat()
        bm = None
        if bm_raw:
            bm_raw = _dump(bm_raw)
            bm = BenchmarkInfo(
                distance=_distance_label(bm_raw.get("distance") or bm_raw.get("distance_km")),
                time_seconds=bm_raw.get("time_seconds") or bm_raw.get("time_sec"),
            )
        return PlanView(
            athlete=AthleteInfo(
                level=level,
                injury=InjuryInfo(active=_injury_active(athlete_raw)),
            ),
            goal=GoalInfo(distance=goal_distance, race_date=race_date),
            benchmark=bm,
            availability=_normalize_availability(avail_src),
            weeks=weeks,
            warnings=list((_dump(data.get("meta")) or {}).get("warnings") or []),
            pace_zones=_normalize_pace_zones(data.get("pace_zones")),
        )

    # Flat EngineValid fixture shape
    if not isinstance(data, dict):
        raise TypeError(f"Unsupported plan type: {type(plan)!r}")

    athlete_raw = _dump(data.get("athlete") or {})
    level = athlete_raw.get("level", "intermediate")
    if hasattr(level, "value"):
        level = level.value
    goal_raw = _dump(data.get("goal") or {})
    bm_raw = data.get("benchmark")
    bm = None
    if bm_raw is not None:
        bm_raw = _dump(bm_raw)
        bm = BenchmarkInfo(
            distance=_distance_label(bm_raw.get("distance") or bm_raw.get("distance_km")),
            time_seconds=bm_raw.get("time_seconds") or bm_raw.get("time_sec"),
        )
    race_date = goal_raw.get("race_date")
    if isinstance(race_date, date):
        race_date = race_date.isoformat()
    avail = data.get("availability")
    if avail is None and athlete_raw:
        avail = athlete_raw.get("availability")
    weeks_raw = data.get("weeks") or []
    return PlanView(
        athlete=AthleteInfo(
            level=str(level),
            injury=InjuryInfo(active=_injury_active(athlete_raw)),
        ),
        goal=GoalInfo(
            distance=_distance_label(goal_raw.get("distance") or goal_raw.get("distance_km")),
            race_date=race_date,
        ),
        benchmark=bm,
        availability=_normalize_availability(avail),
        weeks=[_week_from_raw(w) for w in weeks_raw],
        warnings=list(data.get("warnings") or []),
        pace_zones=_normalize_pace_zones(data.get("pace_zones")),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _weekday_key(session: SessionView) -> str | None:
    if session.weekday:
        return str(session.weekday).lower()[:3]
    d = _parse_date(session.date)
    if d is not None:
        return _WEEKDAY_ORDER[d.weekday()]
    return None


def _session_date(session: SessionView) -> date | None:
    return _parse_date(session.date)


def _week_km(week: WeekView) -> float:
    return float(
        sum(float(s.distance_km or 0.0) for s in week.sessions if s.kind != "rest")
    )


def _week_easy_share(week: WeekView) -> float | None:
    run_sessions = [s for s in week.sessions if s.kind not in ("rest", "strength")]
    if not run_sessions:
        return None
    total_km = sum(float(s.distance_km or 0.0) for s in run_sessions)
    if total_km > 0:
        easy_km = sum(
            float(s.distance_km or 0.0) for s in run_sessions if s.kind in C.EASY_FAMILY
        )
        return easy_km / total_km
    total_min = sum(float(s.total_minutes_est or 0.0) for s in run_sessions)
    if total_min <= 0:
        return None
    easy_min = sum(
        float(s.total_minutes_est or 0.0)
        for s in run_sessions
        if s.kind in C.EASY_FAMILY
    )
    return easy_min / total_min


def _long_km(week: WeekView) -> float:
    return float(
        sum(float(s.distance_km or 0.0) for s in week.sessions if s.kind == "long")
    )


def _is_load_week(week: WeekView) -> bool:
    if week.is_deload:
        return False
    phase = (week.phase or "").lower()
    return phase not in ("taper", "race")


def _day_max_minutes(availability: AvailabilityInfo, weekday: str | None) -> int | None:
    if not weekday:
        return None
    key = weekday.lower()[:3]
    day = availability.days.get(key)
    if day is None:
        for k, v in availability.days.items():
            if str(k).lower()[:3] == key:
                day = v
                break
    if day is None:
        return None
    return day.max_minutes


def _err(
    code: str,
    message: str,
    rule_id: str | None = None,
    **details: Any,
) -> ValidationError:
    payload: dict[str, Any] = {}
    if rule_id is not None:
        payload["rule_id"] = rule_id
    payload.update({k: v for k, v in details.items() if v is not None})
    return ValidationError(
        code=code,
        message=message,
        rule_id=rule_id,
        details=payload or None,
    )


# ---------------------------------------------------------------------------
# Rule checks
# ---------------------------------------------------------------------------
def _check_benchmark(plan: PlanView, errors: list[ValidationError]) -> None:
    bm = plan.benchmark
    if bm is None or bm.time_seconds is None:
        return
    distance = (bm.distance or "5k").lower()
    bounds = C.BENCHMARK_BOUNDS_SEC.get(distance)
    if bounds is None:
        return
    lo, hi = bounds
    t = int(bm.time_seconds)
    if t < lo or t > hi:
        errors.append(
            _err(
                _code(ErrorCode.BENCHMARK_IMPLAUSIBLE),
                f"Benchmark {distance} time {t}s outside plausible range [{lo}, {hi}]",
                rule_id="R17",
                distance=distance,
                time_seconds=t,
                min_sec=lo,
                max_sec=hi,
            )
        )


# Adjacent zones (faster, slower) whose bands must not overlap: R < I < T < M.
PACE_RANGE_ADJACENT_PAIRS: tuple[tuple[str, str], ...] = (("R", "I"), ("I", "T"), ("T", "M"))


def _mmss(sec: float) -> str:
    total = round(sec)
    return f"{total // 60}:{total % 60:02d}"


def _check_pace_ranges(plan: PlanView, errors: list[ValidationError]) -> None:
    """R22 PACE_RANGE_INVALID (ADR-007 / coaching-rules §3.9).

    For every zone carrying a range: min < max and min <= centre <= max. For
    adjacent zones R/I, I/T, T/M: faster.max <= slower.min (no overlap). A zone
    without a range is skipped (backward compatible with pre-P0-6 plans).
    """
    zones = plan.pace_zones
    valid_band: set[str] = set()
    for key in sorted(zones):
        z = zones[key]
        lo, hi = z.range_min, z.range_max
        if lo is None or hi is None:
            continue
        if lo >= hi:
            errors.append(
                _err(
                    _code(ErrorCode.VALIDATION_FAILED),
                    f"Zone {key} : allure min {_mmss(lo)} /km pas plus rapide que la "
                    f"max {_mmss(hi)} /km (la borne min doit être < la borne max)",
                    rule_id="R22",
                    rule_name="PACE_RANGE_INVALID",
                    check="MIN_NOT_BELOW_MAX",
                    zone=key,
                    min_sec_per_km=lo,
                    max_sec_per_km=hi,
                    pace_sec_per_km=z.pace_sec_per_km,
                )
            )
            continue
        valid_band.add(key)
        c = z.pace_sec_per_km
        if c is not None and not (lo <= c <= hi):
            errors.append(
                _err(
                    _code(ErrorCode.VALIDATION_FAILED),
                    f"Zone {key} : allure centrale {_mmss(c)} /km hors de la fourchette "
                    f"{_mmss(lo)}–{_mmss(hi)} /km",
                    rule_id="R22",
                    rule_name="PACE_RANGE_INVALID",
                    check="CENTER_OUTSIDE_RANGE",
                    zone=key,
                    min_sec_per_km=lo,
                    max_sec_per_km=hi,
                    pace_sec_per_km=c,
                )
            )
    for fast, slow in PACE_RANGE_ADJACENT_PAIRS:
        if fast not in valid_band or slow not in valid_band:
            continue
        f, sl = zones[fast], zones[slow]
        f_lo, f_hi, s_lo, s_hi = f.range_min, f.range_max, sl.range_min, sl.range_max
        if f_lo is None or f_hi is None or s_lo is None or s_hi is None:
            continue
        if f_hi > s_lo:
            errors.append(
                _err(
                    _code(ErrorCode.VALIDATION_FAILED),
                    f"Zones {fast}/{slow} : la fourchette {fast} "
                    f"({_mmss(f_lo)}–{_mmss(f_hi)} /km) déborde sur la "
                    f"zone {slow} plus lente ({_mmss(s_lo)}–{_mmss(s_hi)} /km)",
                    rule_id="R22",
                    rule_name="PACE_RANGE_INVALID",
                    check="ADJACENT_ZONES_OVERLAP",
                    zone=fast,
                    slower_zone=slow,
                    fast_max_sec_per_km=f_hi,
                    slow_min_sec_per_km=s_lo,
                )
            )


def _check_weekly_jumps(plan: PlanView, errors: list[ValidationError]) -> None:
    """R01/R02 on load→load progression (ADR-005).

    Week-to-week Δ is vs the last load week (`is_deload=false`), not vs a
    deload. Rebound deload→charge is not an R01 fail; compare the new load
    week to the previous load week. Taper/race weeks are skipped.
    """
    weeks = sorted(plan.weeks, key=lambda w: w.week_index)
    last_load_km: float | None = None
    last_load_week: int | None = None
    # (ratio, from_week, to_week) for consecutive load→load steps (R02)
    load_steps: list[tuple[float, int, int]] = []

    for w in weeks:
        phase = (w.phase or "").lower()
        if phase in ("taper", "race"):
            continue
        if w.is_deload or phase == "deload":
            # Do not update last_load; do not R01-check into the deload.
            continue

        cur_km = _week_km(w)
        if last_load_km is not None and last_load_km > 0 and last_load_week is not None:
            ratio = (cur_km - last_load_km) / last_load_km
            load_steps.append((ratio, last_load_week, w.week_index))
            if ratio > C.MAX_WEEKLY_INCREASE_HARD:
                errors.append(
                    _err(
                        _code(ErrorCode.VALIDATION_FAILED),
                        f"Weekly volume jump {ratio:.1%} exceeds hard max "
                        f"{C.MAX_WEEKLY_INCREASE_HARD:.0%} "
                        f"(week {last_load_week}→{w.week_index})",
                        rule_id="VOLUME_JUMP_TOO_HIGH",
                        from_week=last_load_week,
                        to_week=w.week_index,
                        from_km=last_load_km,
                        to_km=cur_km,
                        increase_ratio=round(ratio, 4),
                    )
                )
        last_load_km = cur_km
        last_load_week = w.week_index

    for i in range(1, len(load_steps)):
        prev_inc, wa, wb = load_steps[i - 1]
        cur_inc, wb2, wc = load_steps[i]
        if prev_inc > C.NO_CONSECUTIVE_LARGE_INCREASE_THRESHOLD and cur_inc > 0:
            errors.append(
                _err(
                    _code(ErrorCode.VALIDATION_FAILED),
                    f"Consecutive increases after large jump "
                    f"({prev_inc:.1%} then {cur_inc:.1%}) "
                    f"at weeks {wb2}→{wc}",
                    rule_id="R02",
                    week_a=wa,
                    week_b=wb2,
                    week_c=wc,
                    first_increase=round(prev_inc, 4),
                    second_increase=round(cur_inc, 4),
                )
            )


def _check_deload(plan: PlanView, errors: list[ValidationError]) -> None:
    """R03 cadence + R04 deload fraction vs recent load peak."""
    weeks = sorted(plan.weeks, key=lambda w: w.week_index)
    load_streak = 0
    block_load_kms: list[float] = []
    for w in weeks:
        phase = (w.phase or "").lower()
        if phase in ("taper", "race"):
            load_streak = 0
            block_load_kms = []
            continue
        if w.is_deload or phase == "deload":
            deload_km = _week_km(w)
            if block_load_kms:
                peak = max(block_load_kms)
                if peak > 0:
                    fraction = deload_km / peak
                    if (
                        fraction < C.DELOAD_FRACTION_MIN
                        or fraction > C.DELOAD_FRACTION_MAX
                    ):
                        errors.append(
                            _err(
                                _code(ErrorCode.VALIDATION_FAILED),
                                f"Deload week {w.week_index} is {fraction:.1%} of "
                                f"recent load peak {peak:.1f} km "
                                f"(allowed [{C.DELOAD_FRACTION_MIN:.0%}, "
                                f"{C.DELOAD_FRACTION_MAX:.0%}])",
                                rule_id="R04",
                                week_index=w.week_index,
                                deload_km=deload_km,
                                peak_km=peak,
                                fraction=round(fraction, 4),
                                min_fraction=C.DELOAD_FRACTION_MIN,
                                max_fraction=C.DELOAD_FRACTION_MAX,
                            )
                        )
            load_streak = 0
            block_load_kms = []
            continue
        load_streak += 1
        block_load_kms.append(_week_km(w))
        if load_streak > C.DELOAD_EVERY_WEEKS_MAX:
            errors.append(
                _err(
                    _code(ErrorCode.VALIDATION_FAILED),
                    f"No deload within {C.DELOAD_EVERY_WEEKS_MAX} load weeks "
                    f"(streak={load_streak} at week {w.week_index})",
                    rule_id="R03",
                    week_index=w.week_index,
                    load_streak=load_streak,
                    max_allowed=C.DELOAD_EVERY_WEEKS_MAX,
                )
            )


def _check_easy_share(plan: PlanView, errors: list[ValidationError]) -> None:
    for w in plan.weeks:
        if not _is_load_week(w):
            continue
        share = _week_easy_share(w)
        if share is None:
            continue
        if share < C.EASY_SHARE_MIN_LOAD_WEEK:
            errors.append(
                _err(
                    _code(ErrorCode.VALIDATION_FAILED),
                    f"Easy share {share:.1%} < {C.EASY_SHARE_MIN_LOAD_WEEK:.0%} "
                    f"on load week {w.week_index}",
                    rule_id="INSUFFICIENT_EASY_RATIO",
                    week_index=w.week_index,
                    easy_share=round(share, 4),
                    min_required=C.EASY_SHARE_MIN_LOAD_WEEK,
                )
            )


def _check_quality_counts(plan: PlanView, errors: list[ValidationError]) -> None:
    for w in plan.weeks:
        hard = [s for s in w.sessions if s.kind in C.QUALITY_HARD]
        tempo = [s for s in w.sessions if s.kind in C.QUALITY_TEMPO]
        if len(hard) > C.MAX_VERY_HARD_QUALITY_PER_WEEK:
            errors.append(
                _err(
                    _code(ErrorCode.VALIDATION_FAILED),
                    f"Week {w.week_index} has {len(hard)} QUALITY_HARD sessions "
                    f"(max {C.MAX_VERY_HARD_QUALITY_PER_WEEK})",
                    rule_id="R06",
                    week_index=w.week_index,
                    count=len(hard),
                    kinds=[s.kind for s in hard],
                )
            )
        if len(tempo) > C.MAX_TEMPO_QUALITY_PER_WEEK:
            errors.append(
                _err(
                    _code(ErrorCode.VALIDATION_FAILED),
                    f"Week {w.week_index} has {len(tempo)} QUALITY_TEMPO sessions "
                    f"(max {C.MAX_TEMPO_QUALITY_PER_WEEK})",
                    rule_id="R07",
                    week_index=w.week_index,
                    count=len(tempo),
                    kinds=[s.kind for s in tempo],
                )
            )


def _check_quality_consecutive(plan: PlanView, errors: list[ValidationError]) -> None:
    if not C.FORBID_HARD_QUALITY_CONSECUTIVE_DAYS:
        return
    dated: list[tuple[date, SessionView, int]] = []
    for w in plan.weeks:
        for s in w.sessions:
            if s.kind not in C.QUALITY_ANY:
                continue
            d = _session_date(s)
            if d is not None:
                dated.append((d, s, w.week_index))
    dated.sort(key=lambda t: t[0])
    for i in range(1, len(dated)):
        d0, s0, w0 = dated[i - 1]
        d1, s1, w1 = dated[i]
        if (d1 - d0).days == 1:
            errors.append(
                _err(
                    _code(ErrorCode.VALIDATION_FAILED),
                    f"Quality sessions on consecutive days "
                    f"({s0.kind} {d0.isoformat()} then {s1.kind} {d1.isoformat()})",
                    rule_id="QUALITY_BACK_TO_BACK",
                    day_a=d0.isoformat(),
                    day_b=d1.isoformat(),
                    kind_a=s0.kind,
                    kind_b=s1.kind,
                    week_a=w0,
                    week_b=w1,
                )
            )
    wd_idx = {name: i for i, name in enumerate(_WEEKDAY_ORDER)}
    for w in plan.weeks:
        quals = [
            s
            for s in w.sessions
            if s.kind in C.QUALITY_ANY and _session_date(s) is None
        ]
        idxs: list[tuple[int, SessionView]] = []
        for s in quals:
            wk = _weekday_key(s)
            if wk in wd_idx:
                idxs.append((wd_idx[wk], s))
        idxs.sort(key=lambda t: t[0])
        for i in range(1, len(idxs)):
            if idxs[i][0] - idxs[i - 1][0] == 1:
                errors.append(
                    _err(
                        _code(ErrorCode.VALIDATION_FAILED),
                        f"Quality sessions on consecutive weekdays in week "
                        f"{w.week_index} ({idxs[i - 1][1].kind} then {idxs[i][1].kind})",
                        rule_id="QUALITY_BACK_TO_BACK",
                        week_index=w.week_index,
                        kind_a=idxs[i - 1][1].kind,
                        kind_b=idxs[i][1].kind,
                    )
                )


def _check_day_after_long(plan: PlanView, errors: list[ValidationError]) -> None:
    allowed = set(C.DAY_AFTER_LONG_ALLOWED)
    dated: list[tuple[date, SessionView, int]] = []
    for w in plan.weeks:
        for s in w.sessions:
            d = _session_date(s)
            if d is not None:
                dated.append((d, s, w.week_index))
    dated.sort(key=lambda t: t[0])
    by_date = {d: (s, wi) for d, s, wi in dated}
    for d, s, wi in dated:
        if s.kind != "long":
            continue
        nxt = d + timedelta(days=1)
        if nxt not in by_date:
            continue
        ns, nwi = by_date[nxt]
        if ns.kind not in allowed:
            errors.append(
                _err(
                    _code(ErrorCode.VALIDATION_FAILED),
                    f"Day after long ({d.isoformat()}) is '{ns.kind}', "
                    f"allowed={sorted(allowed)}",
                    rule_id="R09",
                    long_date=d.isoformat(),
                    next_date=nxt.isoformat(),
                    next_kind=ns.kind,
                    week_index=wi,
                    next_week_index=nwi,
                )
            )
    wd_idx = {name: i for i, name in enumerate(_WEEKDAY_ORDER)}
    for w in plan.weeks:
        sessions = [(_weekday_key(s), s) for s in w.sessions]
        for wk, s in sessions:
            if s.kind != "long" or wk is None or wk not in wd_idx:
                continue
            if _session_date(s) is not None:
                continue
            next_i = wd_idx[wk] + 1
            if next_i >= len(_WEEKDAY_ORDER):
                continue
            next_wd = _WEEKDAY_ORDER[next_i]
            for wk2, s2 in sessions:
                if wk2 == next_wd and s2.kind not in allowed:
                    errors.append(
                        _err(
                            _code(ErrorCode.VALIDATION_FAILED),
                            f"Day after long ({wk}) is '{s2.kind}' in week "
                            f"{w.week_index}, allowed={sorted(allowed)}",
                            rule_id="R09",
                            week_index=w.week_index,
                            long_weekday=wk,
                            next_kind=s2.kind,
                        )
                    )


def _check_long_share(plan: PlanView, errors: list[ValidationError]) -> None:
    level = (plan.athlete.level or "intermediate").lower()
    cap = C.LONG_RUN_SHARE_MAX.get(level, C.LONG_RUN_SHARE_MAX_INTERMEDIATE)
    if plan.athlete.injury.active:
        cap = min(cap, C.INJURY_LONG_RUN_SHARE_CAP)
    for w in plan.weeks:
        total = _week_km(w)
        if total <= 0:
            continue
        long_km = _long_km(w)
        if long_km <= 0:
            continue
        share = long_km / total
        if share > cap:
            errors.append(
                _err(
                    _code(ErrorCode.VALIDATION_FAILED),
                    f"Long-run share {share:.1%} > max {cap:.0%} for level={level} "
                    f"(week {w.week_index})",
                    rule_id="LONG_RUN_OVER_CEILING",
                    week_index=w.week_index,
                    long_km=long_km,
                    week_km=total,
                    share=round(share, 4),
                    max_share=cap,
                    level=level,
                )
            )


def _check_session_max_minutes(plan: PlanView, errors: list[ValidationError]) -> None:
    if not C.SESSION_MUST_RESPECT_MAX_MINUTES:
        return
    for w in plan.weeks:
        for s in w.sessions:
            if s.total_minutes_est is None:
                continue
            wd = _weekday_key(s)
            mx = _day_max_minutes(plan.availability, wd)
            if mx is None:
                continue
            if float(s.total_minutes_est) > float(mx):
                errors.append(
                    _err(
                        _code(ErrorCode.VALIDATION_FAILED),
                        f"Session {s.kind} on {wd} is {s.total_minutes_est} min "
                        f"> max_minutes {mx}",
                        rule_id="SESSION_OVER_MAX_MINUTES",
                        week_index=w.week_index,
                        weekday=wd,
                        kind=s.kind,
                        total_minutes_est=s.total_minutes_est,
                        max_minutes=mx,
                    )
                )


def _check_beginner_hard(plan: PlanView, errors: list[ValidationError]) -> None:
    level = (plan.athlete.level or "").lower()
    if level != "beginner":
        return
    for w in plan.weeks:
        for s in w.sessions:
            if s.kind in C.QUALITY_HARD:
                errors.append(
                    _err(
                        _code(ErrorCode.VALIDATION_FAILED),
                        f"Beginner plan contains QUALITY_HARD kind '{s.kind}' "
                        f"(week {w.week_index})",
                        rule_id="BEGINNER_AGGRESSIVE_REPS",
                        week_index=w.week_index,
                        kind=s.kind,
                        level=level,
                    )
                )


def _check_injury_quality(plan: PlanView, errors: list[ValidationError]) -> None:
    if not plan.athlete.injury.active:
        return
    blocked: set[str] = set()
    if C.INJURY_BLOCKS_QUALITY_HARD:
        blocked |= set(C.QUALITY_HARD)
    if C.INJURY_BLOCKS_QUALITY_TEMPO:
        blocked |= set(C.QUALITY_TEMPO)
    for w in plan.weeks:
        for s in w.sessions:
            if s.kind in blocked:
                errors.append(
                    _err(
                        _code(ErrorCode.INJURY_BLOCKS_QUALITY),
                        f"Injury active blocks quality kind '{s.kind}' "
                        f"(week {w.week_index})",
                        rule_id="R13",
                        week_index=w.week_index,
                        kind=s.kind,
                    )
                )


def _check_taper(plan: PlanView, errors: list[ValidationError]) -> None:
    race_date = _parse_date(plan.goal.race_date)
    has_race_marker = race_date is not None
    for w in plan.weeks:
        if (w.phase or "").lower() == "race":
            has_race_marker = True
    if not has_race_marker:
        return

    taper_weeks = [w for w in plan.weeks if (w.phase or "").lower() == "taper"]
    if not taper_weeks:
        errors.append(
            _err(
                _code(ErrorCode.VALIDATION_FAILED),
                "Race present in plan but no taper phase found",
                rule_id="MISSING_TAPER",
                race_date=plan.goal.race_date,
                distance=plan.goal.distance,
            )
        )
        return

    distance = (plan.goal.distance or "10k").lower()
    taper_range = C.TAPER_DAYS.get(distance)
    if taper_range is None or race_date is None:
        return
    tmin, tmax = taper_range
    taper_dates: list[date] = []
    for w in taper_weeks:
        for s in w.sessions:
            d = _session_date(s)
            if d is not None:
                taper_dates.append(d)
    if not taper_dates:
        return
    taper_start = min(taper_dates)
    duration = (race_date - taper_start).days
    if duration < tmin or duration > tmax:
        errors.append(
            _err(
                _code(ErrorCode.VALIDATION_FAILED),
                f"Taper duration {duration}d outside [{tmin}, {tmax}] for {distance}",
                rule_id="MISSING_TAPER",
                race_date=race_date.isoformat(),
                taper_start=taper_start.isoformat(),
                duration_days=duration,
                min_days=tmin,
                max_days=tmax,
                distance=distance,
            )
        )


def _check_peak_volume(plan: PlanView, errors: list[ValidationError]) -> None:
    level = (plan.athlete.level or "intermediate").lower()
    distance = (plan.goal.distance or "10k").lower()
    caps = C.PEAK_WEEKLY_KM_MAX.get(level)
    if not caps:
        return
    cap = caps.get(distance)
    if cap is None:
        return
    peak = 0.0
    peak_week = None
    for w in plan.weeks:
        km = _week_km(w)
        if km > peak:
            peak = km
            peak_week = w.week_index
    if peak > cap:
        errors.append(
            _err(
                _code(ErrorCode.VALIDATION_FAILED),
                f"Peak weekly volume {peak:.1f} km > max {cap} for "
                f"{level}/{distance}",
                rule_id="R15",
                peak_weekly_km=peak,
                max_allowed=cap,
                level=level,
                distance=distance,
                week_index=peak_week,
            )
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def validate_plan(plan: Any) -> ValidationResult:
    """Validate a plan; never raises for rule failures — returns errors."""
    try:
        coerced = _coerce_plan(plan)
    except Exception as exc:  # noqa: BLE001
        return ValidationResult(
            ok=False,
            errors=[
                _err(
                    _code(ErrorCode.VALIDATION_FAILED),
                    f"Plan could not be parsed: {exc}",
                    rule_id=None,
                )
            ],
        )

    errors: list[ValidationError] = []
    _check_benchmark(coerced, errors)
    _check_pace_ranges(coerced, errors)
    _check_weekly_jumps(coerced, errors)
    _check_deload(coerced, errors)
    _check_easy_share(coerced, errors)
    _check_quality_counts(coerced, errors)
    _check_quality_consecutive(coerced, errors)
    _check_day_after_long(coerced, errors)
    _check_long_share(coerced, errors)
    _check_session_max_minutes(coerced, errors)
    _check_beginner_hard(coerced, errors)
    _check_injury_quality(coerced, errors)
    _check_taper(coerced, errors)
    _check_peak_volume(coerced, errors)

    return ValidationResult(ok=len(errors) == 0, errors=errors)


def validate_plan_or_raise(plan: Any) -> ValidationResult:
    """Like validate_plan but raises EngineError on first blocking failure."""
    result = validate_plan(plan)
    if not result.ok and result.errors:
        first = result.errors[0]
        raise EngineError(
            code=first.code,
            message=first.message,
            message_fr=first.message,
            details=first.details,
            blocking=True,
            rule_id=first.rule_id,
        )
    return result
