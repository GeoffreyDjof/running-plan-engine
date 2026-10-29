"""Filet de propriétés autour de generate_plan.

Ne corrige pas le planner. Pinne le contrat que la prochaine PR devra rétablir.
Les profils blessés (constraints.injuries non vide) sont exclus. Le mode blessure
est un choix produit pas encore tranché.

Invariants
----------
I1. generate_plan ne lève aucune exception sur un PlanRequest Pydantic-valide.
    Un EngineError typé (refus métier) est un résultat, pas un crash.
I2. Tout Plan renvoyé passe validate_plan avec le contexte athlète (_request).
I3. Aucune semaine de charge n'a un volume réel sous 0,9 x le volume réel de S1.
    Charge = is_deload faux et phase hors taper/race (R04 et affûtage §3.5).
    Volume = somme des total_km, pas target_km. Seuil 0,9 = _AVAILABILITY_WARN_RATIO.
I4. Aucune séance hors course n'a total_km < 2,0 km. Course = date == race_date
    ou titre "Course ...".
I5. Aucune séance hors course n'est posée un jour absent ou à max_minutes == 0.
    La course du jour J est exemptée. Le footing pré-course ne l'est pas.

Générateur stdlib random, seed 20261002, N=1000, as_of 2026-10-02. Templates v1
seulement, pas d'hypothesis.
"""

from __future__ import annotations

import datetime as dt
import random
from collections.abc import Sequence

import pytest

from plan_engine.models import (
    Athlete,
    AthleteConstraints,
    Benchmark,
    DayAvailability,
    EngineError,
    Goal,
    Level,
    Options,
    Plan,
    PlanRequest,
    Weekday,
)
from plan_engine.planner import generate_plan
from plan_engine.validator import validate_plan

AS_OF = dt.date(2026, 10, 2)
SEED = 20261002
N_REQUESTS = 1000
WEEKDAYS = list(Weekday)
DISTANCES = (5.0, 10.0, 21.0975)
WEEKS = {5.0: 10, 10.0: 11, 21.0975: 12}
_MIN = {"beginner": (10.0, 13.0, 15.0), "intermediate": (16.0, 20.0, 20.0), "advanced": (26.0, 29.0, 29.0)}
MIN_RECENT = {
    (Level[level], dist): km
    for level, kms in _MIN.items()
    for dist, km in zip(DISTANCES, kms, strict=True)
}
BENCH_BOUNDS = {5.0: (750, 3600), 10.0: (1560, 7200), 21.0975: (3480, 14400)}
LOAD_FLOOR = 0.9
MIN_SESSION_KM = 2.0

def _repro(level, recent, days, distance, race, bench=None):
    athlete = {
        "level": level,
        "recent_weekly_km": recent,
        "availability": [{"weekday": wd, "max_minutes": m} for wd, m in days],
        "constraints": {"injuries": []},
    }
    body = {
        "athlete": athlete,
        "goal": {"distance_km": distance, "race_date": race},
        "options": {"sessions_per_week": 3 if level == "beginner" else 4, "as_of_date": "2026-10-02"},
    }
    if bench:
        body["benchmark"] = {"distance_km": bench[0], "time_sec": bench[1]}
    return body


I1_REPRO = _repro("beginner", [10, 10, 10, 10], (("tue", 90), ("wed", 120), ("sat", 120)), 5.0, "2027-01-02", (5.0, 2500))
I3_REPRO = _repro(
    "beginner", [40, 40, 40, 40], (("wed", 80), ("fri", 80), ("thu", 150)), 21.0975, "2027-01-30", (21.0975, 5400)
)
I5_REPRO = _repro("beginner", [16, 18, 17, 19], (("tue", 50), ("thu", 50), ("sun", 90)), 5.0, "2026-12-13")

I1_REASON = (
    "I1 ValidationError StructureBlock.duration_min<0. Repro beginner 5k "
    "recent=[10,10,10,10] tue90/wed120/sat120 bench 5k@2500s as_of=2026-10-02 "
    "race=2027-01-02 (_split_easy part negative, #17)."
)
I3_REASON = (
    "I3 beginner semi recent=[40]*4 wed80/fri80/thu150 bench 1h30 "
    "as_of=2026-10-02 race=2027-01-30. S1=23.6 then S2=19.6 (<0.9xS1), "
    "collapse to 1.1 km in S6. Healthy on 38a4c14."
)
I4_REASON = "I4 same request as I3. w6-wed-easy 1.1 km. Healthy on 38a4c14."
I5_REASON = (
    "I5 beginner 5k tue/thu/sun race=2026-12-13. Preday Saturday undeclared."
)


def _sessions_for(level: Level) -> int:
    return 3 if level is Level.beginner else 4


def make_request(rng: random.Random, index: int) -> PlanRequest:
    level = rng.choice(list(Level))
    distance = rng.choice(DISTANCES)
    sessions = _sessions_for(level)
    n_days = rng.randint(sessions, 7)
    availability = [
        DayAvailability(
            weekday=wd,
            max_minutes=(
                rng.choice((0, 30, 35, 40, 45))
                if rng.random() < 0.25
                else rng.choice((50, 60, 70, 80, 90, 120, 150))
            ),
        )
        for wd in rng.sample(WEEKDAYS, n_days)
    ]
    usable = sum(1 for d in availability if d.max_minutes > 0)
    if usable < sessions:
        for d in availability:
            if d.max_minutes == 0:
                d.max_minutes = 60
                usable += 1
                if usable >= sessions:
                    break
        extras = [wd for wd in WEEKDAYS if wd not in {d.weekday for d in availability}]
        for wd in extras:
            if usable >= sessions:
                break
            availability.append(DayAvailability(weekday=wd, max_minutes=60))
            usable += 1

    floor = MIN_RECENT[(level, distance)]
    base = rng.uniform(floor, min(70.0, floor + 40.0))
    recent = [round(max(floor, base + rng.uniform(-4.0, 4.0)), 1) for _ in range(4)]
    weeks = WEEKS[distance]
    if rng.random() < 0.15:
        race_date = AS_OF + dt.timedelta(days=rng.randint(14, weeks * 7 - 4))
    else:
        race_date = AS_OF + dt.timedelta(days=weeks * 7 + rng.randint(3, 40))

    benchmark = None
    if rng.random() < 0.6:
        bdist = rng.choice(DISTANCES)
        lo, hi = BENCH_BOUNDS[bdist]
        benchmark = Benchmark(
            distance_km=bdist,
            time_sec=rng.randint(lo, hi),
            date=AS_OF - dt.timedelta(days=rng.randint(7, 90)),
            is_estimate=rng.choice((False, True)),
        )

    return PlanRequest(
        athlete=Athlete(
            id=f"prop-{index}",
            age=rng.randint(18, 70),
            sex=rng.choice(("female", "male", "other")),
            experience_years=round(rng.uniform(0.2, 15.0), 1),
            level=level,
            recent_weekly_km=recent,
            longest_run_km_last_4w=round(max(recent) * rng.uniform(0.25, 0.45), 1),
            availability=availability,
            constraints=AthleteConstraints(injuries=[], no_track=rng.choice((False, True))),
        ),
        benchmark=benchmark,
        goal=Goal(distance_km=distance, race_date=race_date),
        options=Options(sessions_per_week=sessions, as_of_date=AS_OF),
    )


def week_km(week) -> float:
    return round(sum(s.total_km or 0.0 for s in week.sessions), 1)


def is_load(week) -> bool:
    return (not week.is_deload) and week.phase.value not in ("taper", "race")


def is_race_session(session, request: PlanRequest) -> bool:
    if request.goal.race_date is not None and session.date == request.goal.race_date:
        return True
    return session.title.startswith("Course ")


def run_generate(request: PlanRequest) -> Plan | EngineError | BaseException:
    try:
        return generate_plan(request)
    except Exception as exc:  # noqa: BLE001
        return exc


def check_i2(request: PlanRequest, plan: Plan) -> str | None:
    payload = plan.model_dump(mode="json")
    payload["_request"] = request.model_dump(mode="json")
    vr = validate_plan(payload)
    if vr.ok:
        return None
    return f"validate_plan: {[e.rule_id for e in vr.errors]}"


def check_i3(_request: PlanRequest, plan: Plan) -> str | None:
    s1 = week_km(plan.plan[0])
    floor = LOAD_FLOOR * s1
    for w in plan.plan:
        if is_load(w) and week_km(w) < floor:
            return f"S{w.week_index} {week_km(w)} km < {floor:.2f} (S1={s1})"
    return None


def check_i4(request: PlanRequest, plan: Plan) -> str | None:
    for w in plan.plan:
        for s in w.sessions:
            if is_race_session(s, request):
                continue
            km = s.total_km if s.total_km is not None else 0.0
            if km < MIN_SESSION_KM:
                return f"{s.id} {s.kind.value} {km} km"
    return None


def check_i5(request: PlanRequest, plan: Plan) -> str | None:
    days = {d.weekday: d.max_minutes for d in request.athlete.availability}
    for w in plan.plan:
        for s in w.sessions:
            if is_race_session(s, request):
                continue
            minutes = days.get(s.weekday)
            if minutes is None or minutes <= 0:
                return f"{s.id} on {s.weekday.value} minutes={minutes}"
    return None


Outcome = Plan | EngineError | BaseException


@pytest.fixture(scope="module")
def corpus() -> Sequence[tuple[PlanRequest, Outcome]]:
    rng = random.Random(SEED)
    requests = [make_request(rng, i) for i in range(N_REQUESTS)]
    assert len(requests) == N_REQUESTS
    assert all(not r.athlete.constraints.injuries for r in requests)
    return [(req, run_generate(req)) for req in requests]


def _plans(corpus: Sequence[tuple[PlanRequest, Outcome]]):
    for req, out in corpus:
        if isinstance(out, Plan):
            yield req, out


def _failing_plans(corpus, pred) -> list[str]:
    return [f"{req.athlete.id}: {msg}" for req, plan in _plans(corpus) if (msg := pred(req, plan))]


@pytest.mark.xfail(strict=True, reason=I1_REASON)
def test_i1_generate_plan_does_not_raise(corpus: Sequence[tuple[PlanRequest, Outcome]]) -> None:
    crashes = [
        (req.athlete.id, type(out).__name__, str(out).split("\n", 1)[0])
        for req, out in corpus
        if isinstance(out, BaseException)
    ]
    assert crashes == [], crashes[:3]


def test_i2_returned_plan_passes_validate_plan(corpus: Sequence[tuple[PlanRequest, Outcome]]) -> None:
    assert _failing_plans(corpus, check_i2) == []


@pytest.mark.xfail(strict=True, reason=I3_REASON)
def test_i3_load_weeks_stay_near_week1(corpus: Sequence[tuple[PlanRequest, Outcome]]) -> None:
    assert _failing_plans(corpus, check_i3) == []


@pytest.mark.xfail(strict=True, reason=I4_REASON)
def test_i4_non_race_sessions_at_least_2km(corpus: Sequence[tuple[PlanRequest, Outcome]]) -> None:
    assert _failing_plans(corpus, check_i4) == []


@pytest.mark.xfail(strict=True, reason=I5_REASON)
def test_i5_no_session_on_unavailable_day(corpus: Sequence[tuple[PlanRequest, Outcome]]) -> None:
    assert _failing_plans(corpus, check_i5) == []


@pytest.mark.xfail(strict=True, reason=I1_REASON)
def test_i1_reproducer() -> None:
    out = run_generate(PlanRequest.model_validate(I1_REPRO))
    assert not isinstance(out, BaseException), out


@pytest.mark.xfail(strict=True, reason=I3_REASON)
def test_i3_reproducer() -> None:
    req = PlanRequest.model_validate(I3_REPRO)
    out = generate_plan(req)
    assert isinstance(out, Plan) and check_i3(req, out) is None


@pytest.mark.xfail(strict=True, reason=I4_REASON)
def test_i4_reproducer() -> None:
    req = PlanRequest.model_validate(I3_REPRO)
    out = generate_plan(req)
    assert isinstance(out, Plan) and check_i4(req, out) is None


@pytest.mark.xfail(strict=True, reason=I5_REASON)
def test_i5_reproducer() -> None:
    req = PlanRequest.model_validate(I5_REPRO)
    out = generate_plan(req)
    assert isinstance(out, Plan) and check_i5(req, out) is None


def test_generator_is_deterministic() -> None:
    dumps = lambda: [make_request(random.Random(SEED), i).model_dump(mode="json") for i in range(8)]
    assert dumps() == dumps()
