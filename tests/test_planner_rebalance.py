"""Non-régression P0-11 : _split_easy et _rebalance_easy_volume.

#17 plafonne le volume par la disponibilité, mais l'étape « share » de
``_rebalance_easy_volume`` détruisait des km (clip de tous les footings)
et ``_split_easy`` pouvait rendre une part négative. Ces tests figent le
contrat à la source, pas le symptôme I1/I3/I4.
"""

from __future__ import annotations

import datetime as dt

import pytest

from plan_engine.models import (
    DayAvailability,
    EngineError,
    PaceZones,
    Session,
    SessionKind,
    StructureBlock,
    Weekday,
)
from plan_engine.paces import compute_paces
from plan_engine.planner import _rebalance_easy_volume, _split_easy

_MONDAY = dt.date(2026, 10, 5)


def _floor(total: float) -> float:
    return 2.0 if total < 15 else (2.5 if total < 25 else 3.0)


@pytest.mark.parametrize(
    ("total", "n"),
    [
        (6.0, 3),
        (9.0, 3),
        (10.0, 3),
        (7.2, 3),
        (14.9, 3),
        (15.0, 3),
        (4.0, 2),
        (5.0, 2),
        (8.0, 2),
        (24.9, 2),
        (12.0, 1),
    ],
)
def test_split_easy_exact_sum_each_part_at_or_above_floor(total: float, n: int) -> None:
    parts = _split_easy(total, n)
    assert len(parts) == n
    assert round(sum(parts), 1) == round(total, 1)
    assert min(parts) + 1e-9 >= _floor(total)


@pytest.mark.parametrize(
    ("total", "n"),
    [(3.0, 3), (1.5, 2), (0.5, 2), (2.5, 2), (4.0, 3), (0.0, 2)],
)
def test_split_easy_never_negative_and_keeps_exact_sum(total: float, n: int) -> None:
    parts = _split_easy(total, n)
    assert len(parts) == n
    assert all(p >= 0 for p in parts)
    assert round(sum(parts), 1) == round(total, 1)


def test_split_easy_empty_for_non_positive_n() -> None:
    assert _split_easy(10.0, 0) == []
    assert _split_easy(10.0, -1) == []


def _zones() -> PaceZones:
    zones = compute_paces(21.0975, 5400)
    assert not isinstance(zones, EngineError)
    return zones


def _session(sid: str, weekday: Weekday, kind: SessionKind, km: float) -> Session:
    return Session(
        id=sid,
        weekday=weekday,
        date=_MONDAY + dt.timedelta(days=list(Weekday).index(weekday)),
        kind=kind,
        title="Footing easy" if kind != SessionKind.long else "Sortie longue",
        structure=[
            StructureBlock(block="warmup", duration_min=10.0, zone="E"),
            StructureBlock(block="main", distance_km=km, duration_min=max(km * 5.0, 0.0), zone="E"),
            StructureBlock(block="cooldown", duration_min=5.0, zone="E"),
        ],
        total_km=km,
        total_minutes_est=15.0 + km * 5.0,
    )


def _rebalance(sessions: list[Session], week_km: float, days: list[DayAvailability]) -> list[Session]:
    longs = [s for s in sessions if s.kind == SessionKind.long]
    return _rebalance_easy_volume(
        sessions=sessions,
        week_km=week_km,
        days=days,
        level="beginner",
        template_long_cap=0.33,
        long_target_km=longs[0].total_km or 0.0,
        pace_zones=_zones(),
        week_monday=_MONDAY,
        week_index=2,
    )


def test_rebalance_does_not_collapse_below_incoming_when_days_have_room() -> None:
    """I3 S2 avant #17 : 3,6 + 12,4 + 7,2 = 23,2 dans mer80 / ven80 / jeu150.

    Les minutes suffisent à tenir 23,2 km (et la cible 25,8). Le rebalance
    ne doit pas retomber sous le volume déjà posé — c'est le seuil juste
    d'un plafonnement par disponibilité.
    """
    days = [
        DayAvailability(weekday=Weekday.wed, max_minutes=80),
        DayAvailability(weekday=Weekday.fri, max_minutes=80),
        DayAvailability(weekday=Weekday.thu, max_minutes=150),
    ]
    incoming = [
        _session("w2-wed-easy", Weekday.wed, SessionKind.easy, 3.6),
        _session("w2-fri-easy", Weekday.fri, SessionKind.easy, 12.4),
        _session("w2-thu-long", Weekday.thu, SessionKind.long, 7.2),
    ]
    incoming_km = round(sum(s.total_km or 0.0 for s in incoming), 1)
    week_km = 25.8
    out = _rebalance(incoming, week_km, days)
    actual = round(sum(s.total_km or 0.0 for s in out), 1)
    assert actual >= incoming_km - 0.15
    assert actual <= week_km + 1e-9
    foot = [s.total_km or 0.0 for s in out if s.kind in (SessionKind.easy, SessionKind.recovery)]
    long_km = next(s.total_km or 0.0 for s in out if s.kind == SessionKind.long)
    assert min(foot) >= 2.0
    assert long_km <= 0.35 * actual + 1e-9


def test_rebalance_hard_capped_day_does_not_flatten_the_week() -> None:
    """Un lundi à 30 min (2,1 km) ne doit pas ramener mar/mer à 2,3 km."""
    days = [
        DayAvailability(weekday=Weekday.mon, max_minutes=30),
        DayAvailability(weekday=Weekday.tue, max_minutes=70),
        DayAvailability(weekday=Weekday.wed, max_minutes=150),
    ]
    incoming = [
        _session("w1-mon-easy", Weekday.mon, SessionKind.easy, 2.1),
        _session("w1-tue-easy", Weekday.tue, SessionKind.easy, 7.6),
        _session("w1-wed-long", Weekday.wed, SessionKind.long, 4.8),
    ]
    incoming_km = 14.5
    out = _rebalance(incoming, 21.0, days)
    actual = round(sum(s.total_km or 0.0 for s in out), 1)
    assert actual >= incoming_km - 0.15
    by_wd = {s.weekday: s.total_km or 0.0 for s in out}
    assert by_wd[Weekday.tue] >= 4.0


def test_rebalance_tiny_strides_do_not_drag_the_week_down() -> None:
    """I1 S2 : un strides à 1,7 km ne doit pas égaliser la semaine vers 1,8 km."""
    days = [
        DayAvailability(weekday=Weekday.tue, max_minutes=90),
        DayAvailability(weekday=Weekday.wed, max_minutes=120),
        DayAvailability(weekday=Weekday.sat, max_minutes=120),
    ]
    incoming = [
        _session("w2-sat-easy", Weekday.sat, SessionKind.easy, 1.7),
        _session("w2-tue-easy", Weekday.tue, SessionKind.easy, 7.0),
        _session("w2-wed-long", Weekday.wed, SessionKind.long, 3.4),
    ]
    incoming_km = 12.1
    out = _rebalance(incoming, incoming_km, days)
    actual = round(sum(s.total_km or 0.0 for s in out), 1)
    assert actual >= incoming_km - 0.15
    assert min(s.total_km or 0.0 for s in out) >= 2.0
    assert max(s.total_km or 0.0 for s in out) >= 3.4
