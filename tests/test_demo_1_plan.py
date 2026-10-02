"""P0-11: demo_1 (5k débutant, 13,5 km/sem) n'est plus plat et reste sûr.

Critères PlanOrch / DomainCoach / dr eggbot (2 oct. 2026) :
- S1 <= 1,10 x km de référence (13,5 -> 14,85) ;
- aucune semaine de charge sous S1 ; les semaines d'allègement sont exclues
  et bornées à 70-80 % de la semaine de charge précédente ;
- plus long footing <= sortie longue <= 35 % de la semaine (débutant) ;
- les minutes dispo sont un plafond, pas un objectif.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plan_engine import constants as C
from plan_engine.models import Plan, PlanRequest, SessionKind, WeekPlan
from plan_engine.planner import generate_plan, reference_weekly_km

_ROOT = Path(__file__).resolve().parents[1] / "examples"
_DEMO_1 = _ROOT / "demo" / "demo_1_beginner_5k.json"
_EASY = (SessionKind.easy, SessionKind.recovery)


def _load(path: Path) -> PlanRequest:
    return PlanRequest.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _km(week: WeekPlan) -> float:
    return round(sum(s.total_km or 0.0 for s in week.sessions), 1)


def _is_load(week: WeekPlan) -> bool:
    return not week.is_deload and week.phase.value not in ("taper", "race")


@pytest.fixture(scope="module")
def demo_1() -> tuple[PlanRequest, Plan]:
    req = _load(_DEMO_1)
    plan = generate_plan(req)
    assert isinstance(plan, Plan), plan
    return req, plan


def test_week_1_within_start_cap(demo_1: tuple[PlanRequest, Plan]) -> None:
    req, plan = demo_1
    ref = reference_weekly_km(req.athlete.recent_weekly_km)
    assert ref == pytest.approx(13.5)
    assert _km(plan.plan[0]) <= round(C.START_VOLUME_MAX_RATIO * ref, 2)  # 14,85


def test_no_load_week_below_week_1(demo_1: tuple[PlanRequest, Plan]) -> None:
    _, plan = demo_1
    s1 = _km(plan.plan[0])
    for w in plan.plan[1:]:
        if _is_load(w):
            assert _km(w) >= s1, (w.week_index, _km(w), s1)


def test_deload_weeks_in_band(demo_1: tuple[PlanRequest, Plan]) -> None:
    _, plan = demo_1
    prev_load = None
    for w in plan.plan:
        if w.is_deload:
            assert prev_load is not None
            ratio = _km(w) / prev_load
            assert C.DELOAD_FRACTION_MIN <= ratio <= C.DELOAD_FRACTION_MAX, (w.week_index, ratio)
        elif _is_load(w):
            prev_load = _km(w)


def test_plan_is_not_flat(demo_1: tuple[PlanRequest, Plan]) -> None:
    _, plan = demo_1
    loads = [_km(w) for w in plan.plan if _is_load(w)]
    assert max(loads) > loads[0]
    # Ancien bug : S2 à 11,5 km alors que le coureur fait 13,5 km.
    assert min(loads) >= 13.5


def test_long_run_bounds(demo_1: tuple[PlanRequest, Plan]) -> None:
    _, plan = demo_1
    share_max = C.LONG_RUN_SHARE_MAX["beginner"]  # 0,35
    for w in plan.plan:
        if not _is_load(w):
            continue
        longs = [s for s in w.sessions if s.kind == SessionKind.long]
        assert len(longs) == 1, w.week_index
        long_km = longs[0].total_km or 0.0
        foot = [s.total_km or 0.0 for s in w.sessions if s.kind in _EASY]
        assert max(foot) <= long_km, (w.week_index, foot, long_km)
        assert long_km <= share_max * _km(w) + 1e-9, (w.week_index, long_km, _km(w))


def test_minutes_are_a_ceiling(demo_1: tuple[PlanRequest, Plan]) -> None:
    req, plan = demo_1
    caps = {d.weekday: d.max_minutes for d in req.athlete.availability}
    for w in plan.plan:
        for s in w.sessions:
            if s.weekday in caps and s.kind != SessionKind.race_pace:
                assert (s.total_minutes_est or 0.0) <= caps[s.weekday], s.id
    # Dimanche 120 min : la sortie longue ne remplit pas le créneau.
    longs = [s for w in plan.plan for s in w.sessions if s.kind == SessionKind.long]
    assert max(s.total_minutes_est or 0.0 for s in longs) <= 75


def test_capped_volume_is_reported(demo_1: tuple[PlanRequest, Plan]) -> None:
    _, plan = demo_1
    codes = [w.code for w in plan.meta.warnings]
    assert codes == ["VOLUME_CAPPED_BY_AVAILABILITY"]
    assert "minutes disponibles" in plan.meta.warnings[0].message_fr


_INPUTS = sorted(
    p
    for p in [*_ROOT.glob("*.json"), *(_ROOT / "demo").glob("*.json")]
    if not p.name.endswith("_plan_generated.json")
)


@pytest.mark.parametrize("path", _INPUTS, ids=lambda p: p.stem)
def test_long_run_not_shorter_than_footings(path: Path) -> None:
    plan = generate_plan(_load(path))
    if not isinstance(plan, Plan):
        pytest.skip("profil refusé par conception")
    for w in plan.plan:
        if not _is_load(w):
            continue
        longs = [s.total_km or 0.0 for s in w.sessions if s.kind == SessionKind.long]
        foot = [s.total_km or 0.0 for s in w.sessions if s.kind in _EASY]
        if longs and foot:
            assert max(foot) <= longs[0], (path.stem, w.week_index, foot, longs)
