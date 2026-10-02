"""Deterministic planner: PlanRequest → Plan | EngineError.

Templates v1: 5k/10k/half · beginner 3× / intermediate+advanced 4×.
"""

from __future__ import annotations

import datetime as dt
import statistics
from types import ModuleType
from typing import Sequence

from plan_engine import constants as C
from plan_engine.models import (
    DayAvailability,
    EngineError,
    ErrorCode,
    Plan,
    PlanMeta,
    PlanPhase,
    PlanRequest,
    PlanResult,
    Session,
    SessionKind,
    StructureBlock,
    WeekPlan,
    Weekday,
)
from plan_engine.paces import compute_paces, pace_zones_from_vdot, vdot_from_benchmark
from plan_engine.templates import (
    advanced_10k_4x,
    advanced_5k_4x,
    advanced_half_4x,
    beginner_10k_3x,
    beginner_5k_3x,
    beginner_half_3x,
    intermediate_10k_4x,
    intermediate_5k_4x,
    intermediate_half_4x,
)
from plan_engine.validator import ValidationResult, validate_plan

_ENGINE_VERSION = "0.1.0"
_WEEKDAY_ORDER = (
    Weekday.mon,
    Weekday.tue,
    Weekday.wed,
    Weekday.thu,
    Weekday.fri,
    Weekday.sat,
    Weekday.sun,
)

_TEMPLATES: tuple[ModuleType, ...] = (
    beginner_5k_3x,
    intermediate_5k_4x,
    advanced_5k_4x,
    beginner_10k_3x,
    intermediate_10k_4x,
    advanced_10k_4x,
    beginner_half_3x,
    intermediate_half_4x,
    advanced_half_4x,
)


def generate_plan(request: PlanRequest) -> PlanResult:
    """Assemble a deterministic Plan from PlanRequest (no LLM), then validate it.

    Every Plan returned here has passed ``validate_plan`` with the athlete
    context from the request. A plan that fails any safety rule is never
    returned: the caller gets a typed EngineError (INJURY_BLOCKS_QUALITY if an
    injury rule fired, VALIDATION_FAILED otherwise) with rule_id + details.
    """
    result = _assemble_plan(request)
    if isinstance(result, EngineError):
        return result
    return _validated_or_error(result, request)


def _validated_or_error(plan: Plan, request: PlanRequest) -> PlanResult:
    payload = plan.model_dump(mode="json")
    payload["_request"] = request.model_dump(mode="json")
    vr = validate_plan(payload)
    if vr.ok:
        return plan
    return _validation_error(vr)


def _validation_error(vr: ValidationResult) -> EngineError:
    injury = [e for e in vr.errors if e.code == ErrorCode.INJURY_BLOCKS_QUALITY.value]
    first = injury[0] if injury else vr.errors[0]
    code = ErrorCode.INJURY_BLOCKS_QUALITY if injury else ErrorCode.VALIDATION_FAILED
    broken = sorted({e.rule_id for e in vr.errors if e.rule_id})
    return EngineError(
        code=code,
        message_fr=(
            "Plan refusé par le validateur de sécurité "
            f"({first.rule_id or 'parse'}): {first.message}"
        ),
        details={
            "rule_id": first.rule_id,
            "broken_rules": broken,
            "errors": [e.model_dump(mode="json") for e in vr.errors],
        },
    )


def _assemble_plan(request: PlanRequest) -> PlanResult:
    """Build the raw plan from templates. Not validated — use generate_plan."""
    err = _preflight_availability(request)
    if err is not None:
        return err

    tmpl = _select_template(request)
    if tmpl is None:
        goal_key = _goal_distance_key(request.goal.distance_km)
        return EngineError(
            code=ErrorCode.VALIDATION_FAILED,
            message_fr=(
                "Template v1 disponible: 5k/10k/half beginner 3 séances, "
                "intermediate/advanced 4 séances. Marathon en phase suivante."
            ),
            details={
                "level": request.athlete.level.value,
                "goal_distance_key": goal_key,
                "sessions_per_week": request.options.sessions_per_week,
                "supported": [t.TEMPLATE_ID for t in _TEMPLATES],
            },
        )

    err = _preflight_race_date(request, tmpl)
    if err is not None:
        return err

    paces_result, vdot, confidence = _resolve_paces(request)
    if isinstance(paces_result, EngineError):
        return paces_result
    pace_zones = paces_result

    n_weeks = tmpl.WEEKS
    start_date, race_date = _schedule_window(request, n_weeks)

    peak = _peak_km(request, tmpl)
    if isinstance(peak, EngineError):
        return peak

    n_sess = tmpl.SESSIONS_PER_WEEK
    training_days = _pick_training_days(request.athlete.availability, n_sess)
    long_day = max(training_days, key=lambda d: d.max_minutes)
    quality_day = _pick_quality_day(training_days, long_day)
    easy_days = [
        d for d in training_days if d.weekday not in (long_day.weekday, quality_day.weekday)
    ]

    weeks: list[WeekPlan] = []
    last_load_km = 0.0
    block_peak_km = 0.0  # R04: peak within current load block (resets after deload)
    for spec in tmpl.week_specs():
        week_km = round(peak * float(spec["volume_frac"]), 1)
        week_km = min(week_km, tmpl.PEAK_WEEKLY_KM_CAP)
        is_deload = bool(spec["is_deload"])
        if is_deload and block_peak_km > 0:
            # Aim mid-band ~75% so rounding stays in [70%, 80%]
            week_km = round(block_peak_km * 0.75, 1)
        sessions = _build_week_sessions(
            request=request,
            tmpl=tmpl,
            spec=spec,
            week_km=week_km,
            start_date=start_date,
            race_date=race_date,
            long_day=long_day,
            quality_day=quality_day,
            easy_days=easy_days,
            pace_zones=pace_zones,
        )
        actual_km = round(sum(s.total_km or 0.0 for s in sessions), 1)
        if is_deload and block_peak_km > 0:
            lo = block_peak_km * C.DELOAD_FRACTION_MIN
            hi = block_peak_km * C.DELOAD_FRACTION_MAX
            mid = block_peak_km * 0.75
            for _ in range(4):
                if lo <= actual_km <= hi:
                    break
                if actual_km <= 0:
                    break
                week_km = round(week_km * (mid / actual_km), 1)
                sessions = _build_week_sessions(
                    request=request,
                    tmpl=tmpl,
                    spec=spec,
                    week_km=week_km,
                    start_date=start_date,
                    race_date=race_date,
                    long_day=long_day,
                    quality_day=quality_day,
                    easy_days=easy_days,
                    pace_zones=pace_zones,
                )
                actual_km = round(sum(s.total_km or 0.0 for s in sessions), 1)
        weeks.append(
            WeekPlan(
                week_index=int(spec["week_index"]),
                phase=PlanPhase(spec["phase"]),
                target_km=week_km,
                is_deload=is_deload,
                sessions=sessions,
            )
        )
        if is_deload:
            block_peak_km = 0.0
        elif spec["phase"] not in ("taper", "race"):
            last_load_km = actual_km
            block_peak_km = max(block_peak_km, actual_km)

    return Plan(
        meta=PlanMeta(
            engine_version=_ENGINE_VERSION,
            generated_at=dt.datetime(2026, 9, 26, 9, 0, 0, tzinfo=dt.timezone.utc),
            method=f"vdot_templates_v1:{tmpl.TEMPLATE_ID}",
            vdot=round(vdot, 2),
            paces_confidence=confidence,  # type: ignore[arg-type]
            start_date=start_date,
            weeks=n_weeks,
            warnings=[],
        ),
        pace_zones=pace_zones,
        plan=weeks,
    )


def _select_template(request: PlanRequest) -> ModuleType | None:
    goal_key = _goal_distance_key(request.goal.distance_km)
    if goal_key not in ("5k", "10k", "half"):
        return None
    level = request.athlete.level.value
    spw = request.options.sessions_per_week
    for tmpl in _TEMPLATES:
        if (
            tmpl.GOAL_KEY == goal_key
            and tmpl.LEVEL == level
            and tmpl.SESSIONS_PER_WEEK == spw
        ):
            return tmpl
    return None


def _preflight_availability(request: PlanRequest) -> EngineError | None:
    usable = [d for d in request.athlete.availability if d.max_minutes > 0]
    if len(usable) < request.options.sessions_per_week:
        return EngineError(
            code=ErrorCode.INSUFFICIENT_AVAILABILITY,
            message_fr=(
                f"Disponibilité insuffisante: {len(usable)} jour(s) >0 min pour "
                f"{request.options.sessions_per_week} séances/semaine."
            ),
            details={
                "usable_days": len(usable),
                "sessions_per_week": request.options.sessions_per_week,
            },
        )
    return None


def _preflight_race_date(request: PlanRequest, tmpl: ModuleType) -> EngineError | None:
    if request.goal.race_date is None:
        return None
    today = dt.date(2026, 9, 26)
    days = (request.goal.race_date - today).days
    if days < tmpl.WEEKS * 7 - 3:
        return EngineError(
            code=ErrorCode.GOAL_TOO_SOON,
            message_fr=(
                f"Objectif trop proche ({days} jours) pour un plan "
                f"{tmpl.WEEKS} semaines."
            ),
            details={"days_to_race": days, "min_weeks": tmpl.WEEKS},
        )
    return None


def _goal_distance_key(distance_km: float) -> str | None:
    for km, key in C.DISTANCE_KM_TO_KEY.items():
        if abs(distance_km - km) <= 0.05:
            return key
    return None


def _resolve_paces(request: PlanRequest):
    if request.benchmark is not None:
        result = compute_paces(request.benchmark.distance_km, request.benchmark.time_sec)
        if isinstance(result, EngineError):
            return result, 0.0, "low"
        vdot = vdot_from_benchmark(request.benchmark.distance_km, request.benchmark.time_sec)
        conf = "low" if request.benchmark.is_estimate else "high"
        return result, vdot, conf
    # Conservative defaults by level when no benchmark
    defaults = {"beginner": 35.0, "intermediate": 42.0, "advanced": 50.0}
    vdot = defaults.get(request.athlete.level.value, 42.0)
    return pace_zones_from_vdot(vdot), vdot, "low"


def _peak_km(request: PlanRequest, tmpl: ModuleType) -> float | EngineError:
    recent = list(request.athlete.recent_weekly_km)
    if recent:
        start = float(statistics.median(recent))
    else:
        start = {"beginner": 18.0, "intermediate": 30.0, "advanced": 50.0}.get(
            tmpl.LEVEL, 30.0
        )
    bounds = {
        "beginner": (12.0, 32.0) if tmpl.GOAL_KEY != "half" else (18.0, 38.0),
        "intermediate": (22.0, 45.0) if tmpl.GOAL_KEY != "half" else (30.0, 58.0),
        "advanced": (40.0, 72.0) if tmpl.GOAL_KEY != "half" else (50.0, 85.0),
    }
    lo, hi = bounds.get(tmpl.LEVEL, (22.0, 45.0))
    start = max(lo, min(start, hi))
    climb = {"beginner": 1.55, "intermediate": 1.35, "advanced": 1.22}[tmpl.LEVEL]
    floor_peak = {
        "beginner": 24.0 if tmpl.GOAL_KEY != "half" else 28.0,
        "intermediate": tmpl.TARGET_PEAK_KM * 0.85,
        "advanced": 58.0 if tmpl.GOAL_KEY != "half" else 65.0,
    }[tmpl.LEVEL]
    peak = max(start * climb, floor_peak)
    peak = min(float(peak), float(tmpl.TARGET_PEAK_KM), float(tmpl.PEAK_WEEKLY_KM_CAP))
    min_for_goal = {"beginner": 18.0, "intermediate": 18.0, "advanced": 35.0}[tmpl.LEVEL]
    if start < min_for_goal and tmpl.LEVEL != "beginner":
        return EngineError(
            code=ErrorCode.VOLUME_TOO_LOW_FOR_GOAL,
            message_fr="Volume de départ trop bas pour cet objectif / niveau.",
            details={"start_weekly_km": start, "level": tmpl.LEVEL},
        )
    return float(peak)


def _schedule_window(request: PlanRequest, n_weeks: int) -> tuple[dt.date, dt.date]:
    if request.goal.race_date is not None:
        race_date = request.goal.race_date
    else:
        race_date = dt.date(2026, 12, 13)
    race_wd = race_date.weekday()
    last_week_monday = race_date - dt.timedelta(days=race_wd)
    start_date = last_week_monday - dt.timedelta(weeks=n_weeks - 1)
    return start_date, race_date


def _pick_training_days(
    availability: Sequence[DayAvailability], n: int
) -> list[DayAvailability]:
    usable = [d for d in availability if d.max_minutes > 0]
    ranked = sorted(usable, key=lambda d: (-d.max_minutes, _WEEKDAY_ORDER.index(d.weekday)))
    chosen = ranked[:n]
    chosen.sort(key=lambda d: _WEEKDAY_ORDER.index(d.weekday))
    return chosen


def _pick_quality_day(
    training_days: Sequence[DayAvailability], long_day: DayAvailability
) -> DayAvailability:
    candidates = [d for d in training_days if d.weekday != long_day.weekday]
    long_i = _WEEKDAY_ORDER.index(long_day.weekday)

    def score(d: DayAvailability) -> tuple[int, int]:
        i = _WEEKDAY_ORDER.index(d.weekday)
        adj = 0 if abs(i - long_i) % 7 in (1, 6) else 1
        return (adj, d.max_minutes)

    return max(candidates, key=score)


def _build_week_sessions(
    *,
    request: PlanRequest,
    tmpl: ModuleType,
    spec: dict,
    week_km: float,
    start_date: dt.date,
    race_date: dt.date,
    long_day: DayAvailability,
    quality_day: DayAvailability,
    easy_days: Sequence[DayAvailability],
    pace_zones,
) -> list[Session]:
    wi = int(spec["week_index"])
    week_monday = start_date + dt.timedelta(weeks=wi - 1)
    quality = spec.get("quality")
    include_race = bool(spec.get("include_race"))
    is_deload = bool(spec["is_deload"])
    phase = spec["phase"]

    race_wd = _weekday_from_date(race_date)
    easy_use = list(easy_days)
    if include_race:
        easy_use = [d for d in easy_use if d.weekday != race_wd]

    long_share = tmpl.LONG_SHARE_DELOAD if is_deload else tmpl.LONG_SHARE_LOAD
    if phase in ("taper", "race"):
        long_share = min(long_share, tmpl.LONG_SHARE_DELOAD)
    long_km = round(week_km * long_share, 1)
    qual_km = 0.0
    if quality and not is_deload and phase not in ("race",):
        if quality == "strides":
            qual_km = round(week_km * 0.14, 1)
        elif quality == "intervals":
            qual_km = round(week_km * 0.15, 1)
        else:
            qual_km = round(week_km * 0.17, 1)
    remaining = max(week_km - long_km - qual_km, 0.0)
    n_easy_slots = len(easy_use) + (0 if (quality and qual_km > 0) else 1)
    easy_kms = _split_easy(remaining, max(n_easy_slots, 1))

    sessions: list[Session] = []
    easy_i = 0

    def _maybe_add(sess: Session) -> None:
        if phase == "taper":
            _tmin, tmax = C.TAPER_DAYS.get(tmpl.GOAL_KEY, (7, 10))
            earliest = race_date - dt.timedelta(days=int(tmax))
            latest = race_date - dt.timedelta(days=1)
            if sess.date < earliest or sess.date > latest:
                return
        sessions.append(sess)

    if quality and qual_km > 0:
        # strides: neuromusculaire léger — kind=easy pour R05 (EASY_FAMILY), notes strides
        emit_kind = SessionKind.easy if quality == "strides" else SessionKind(quality)
        _maybe_add(
            _make_session(
                week_monday=week_monday,
                day=quality_day,
                kind=emit_kind,
                distance_km=qual_km,
                pace_zones=pace_zones,
                week_index=wi,
                title_fr=_title_fr(quality),
                notes_override=(
                    "Footing easy + 4–6 strides progressifs (pas de reps agressives)."
                    if quality == "strides"
                    else None
                ),
            )
        )
    else:
        ek = easy_kms[easy_i] if easy_i < len(easy_kms) else round(remaining / max(n_easy_slots, 1), 1)
        easy_i += 1
        if not (include_race and quality_day.weekday == race_wd):
            _maybe_add(
                _make_session(
                    week_monday=week_monday,
                    day=quality_day,
                    kind=SessionKind.easy,
                    distance_km=ek,
                    pace_zones=pace_zones,
                    week_index=wi,
                    title_fr="Footing easy",
                )
            )

    for day in easy_use:
        ek = easy_kms[easy_i] if easy_i < len(easy_kms) else 5.0
        easy_i += 1
        kind = SessionKind.recovery if is_deload or phase == "taper" else SessionKind.easy
        _maybe_add(
            _make_session(
                week_monday=week_monday,
                day=day,
                kind=kind,
                distance_km=ek,
                pace_zones=pace_zones,
                week_index=wi,
                title_fr="Récupération" if kind == SessionKind.recovery else "Footing easy",
            )
        )

    if include_race:
        sessions.clear()
        shake_date = race_date - dt.timedelta(days=1)
        shake_wd = _weekday_from_date(shake_date)
        shake_day = next(
            (d for d in [*easy_use, quality_day, long_day] if d.weekday == shake_wd), None
        )
        if shake_day is None:
            shake_day = quality_day
        sessions.append(
            _make_session(
                week_monday=week_monday,
                day=shake_day,
                kind=SessionKind.easy,
                distance_km=(
                    3.0
                    if tmpl.GOAL_KEY == "5k"
                    else (5.0 if tmpl.LEVEL != "beginner" else 3.0)
                ),
                pace_zones=pace_zones,
                week_index=wi,
                title_fr="Footing pré-course",
                force_date=shake_date,
            )
        )
        race_day = next((d for d in request.athlete.availability if d.weekday == race_wd), None)
        min_race_min = 90 if tmpl.GOAL_KEY in ("5k", "10k") else 150
        if race_day is None or race_day.max_minutes < min_race_min:
            race_day = DayAvailability(
                weekday=race_wd,
                max_minutes=max(long_day.max_minutes, min_race_min + 30),
            )
        sessions.append(
            _make_session(
                week_monday=week_monday,
                day=race_day,
                kind=SessionKind.race_pace,
                distance_km=float(tmpl.RACE_DISTANCE_KM),
                pace_zones=pace_zones,
                week_index=wi,
                title_fr=f"Course {tmpl.RACE_DISTANCE_KM:g} km",
                force_date=race_date,
            )
        )
    else:
        long_kind = SessionKind.easy if phase == "taper" else SessionKind.long
        long_title = "Footing long souple" if phase == "taper" else "Sortie longue"
        _maybe_add(
            _make_session(
                week_monday=week_monday,
                day=long_day,
                kind=long_kind,
                distance_km=long_km,
                pace_zones=pace_zones,
                week_index=wi,
                title_fr=long_title,
            )
        )

    if not include_race:
        # Cap long share: long <= cap/(1-cap) * other_km (so share after rebuild ≤ cap)
        hard_max = C.LONG_RUN_SHARE_MAX.get(tmpl.LEVEL, tmpl.LONG_SHARE_CAP) - 0.005
        cap = min(float(tmpl.LONG_SHARE_CAP), hard_max)
        for _ in range(3):
            total = sum(s.total_km or 0.0 for s in sessions)
            longs = [s for s in sessions if s.kind == SessionKind.long]
            if not longs or total <= 0:
                break
            share = (longs[0].total_km or 0.0) / total
            if share <= cap:
                break
            other = total - (longs[0].total_km or 0.0)
            target = round(other * cap / (1.0 - cap), 1)
            target = max(target, 3.0)
            sessions = [s for s in sessions if s.kind != SessionKind.long]
            _maybe_add(
                _make_session(
                    week_monday=week_monday,
                    day=long_day,
                    kind=SessionKind.long,
                    distance_km=target,
                    pace_zones=pace_zones,
                    week_index=wi,
                    title_fr="Sortie longue",
                )
            )

    sessions.sort(key=lambda s: s.date)
    return sessions


def _split_easy(total: float, n: int) -> list[float]:
    if n <= 0:
        return []
    base = round(total / n, 1)
    parts = [base] * n
    drift = round(total - sum(parts), 1)
    parts[-1] = round(parts[-1] + drift, 1)
    floor = 2.0 if total < 15 else (2.5 if total < 25 else 3.0)
    # Do not inflate above requested total (availability clamp handles max)
    parts = [max(p, floor) for p in parts]
    if sum(parts) > total + 0.05 and total > 0:
        scale = total / sum(parts)
        parts = [max(round(p * scale, 1), floor) for p in parts]
        parts[-1] = round(total - sum(parts[:-1]), 1)
    return parts


def _weekday_from_date(d: dt.date) -> Weekday:
    return _WEEKDAY_ORDER[d.weekday()]


def _title_fr(quality: str) -> str:
    return {
        "tempo": "Tempo / seuil",
        "intervals": "Fractionné VMA (I)",
        "race_pace": "Allure spécifique course",
        "cruise_intervals": "Intervalles cruise",
        "strides": "Footing + éducatifs / strides",
    }.get(quality, quality)


def _make_session(
    *,
    week_monday: dt.date,
    day: DayAvailability,
    kind: SessionKind,
    distance_km: float,
    pace_zones,
    week_index: int,
    title_fr: str,
    force_date: dt.date | None = None,
    notes_override: str | None = None,
) -> Session:
    wd_index = _WEEKDAY_ORDER.index(day.weekday)
    date = force_date or (week_monday + dt.timedelta(days=wd_index))
    zone_key = _zone_for_kind(kind)
    pace = getattr(pace_zones, zone_key).pace_sec_per_km
    wu = 10.0 if kind != SessionKind.strides else 8.0
    cd = 5.0
    main_min = (distance_km * pace) / 60.0
    total = wu + main_min + cd
    if day.max_minutes > 0 and total > day.max_minutes:
        budget = max(float(day.max_minutes) - wu - cd, 8.0)
        distance_km = max(round(budget * 60.0 / pace, 1), 2.0)
        main_min = (distance_km * pace) / 60.0
        total = wu + main_min + cd
        if total > day.max_minutes:
            overflow = total - day.max_minutes
            wu = max(wu - overflow, 5.0)
            total = wu + main_min + cd
            if total > day.max_minutes:
                main_min = max(day.max_minutes - wu - cd, 5.0)
                distance_km = round(main_min * 60.0 / pace, 1)
                total = float(day.max_minutes)
    structure = [
        StructureBlock(block="warmup", duration_min=wu, zone="E"),
        StructureBlock(
            block="main",
            distance_km=distance_km,
            duration_min=round(main_min, 1),
            zone=zone_key,  # type: ignore[arg-type]
        ),
        StructureBlock(block="cooldown", duration_min=cd, zone="E"),
    ]
    notes = notes_override or {
        SessionKind.easy: "Allure confortable, conversation possible.",
        SessionKind.recovery: "Très souple, jambes légères.",
        SessionKind.long: "Endurance fondamentale ; rester en zone E.",
        SessionKind.tempo: "Effort contrôlé au seuil (zone T).",
        SessionKind.intervals: "Répétitions zone I ; récupération jogging entre les séries.",
        SessionKind.race_pace: "Allure objectif 10k ; rester lucide sur l'effort.",
        SessionKind.strides: "Footing easy + 4–6 strides progressifs (pas de reps agressives).",
    }.get(kind, "")
    return Session(
        id=f"w{week_index}-{day.weekday.value}-{kind.value}",
        weekday=day.weekday,
        date=date,
        kind=kind,
        title=title_fr,
        structure=structure,
        total_km=round(distance_km, 1),
        total_minutes_est=round(total, 1),
        load=None,
        notes_fr=notes,
    )


def _zone_for_kind(kind: SessionKind) -> str:
    if kind in (SessionKind.tempo, SessionKind.cruise_intervals):
        return "T"
    if kind == SessionKind.intervals:
        return "I"
    if kind == SessionKind.reps:
        return "R"
    if kind == SessionKind.race_pace:
        return "T"
    # strides stay easy-family for volume share
    return "E"
