"""P0-7: no hard-coded today/generated_at; same input + as_of_date -> same JSON."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from plan_engine import planner
from plan_engine.models import EngineError, ErrorCode, Plan, PlanRequest

ROOT = Path(__file__).resolve().parents[1]


def _req(name: str) -> PlanRequest:
    return PlanRequest.model_validate_json((ROOT / "examples" / f"{name}.json").read_text())


def _req_with_options_as_of(name: str, as_of: str) -> PlanRequest:
    data = json.loads((ROOT / "examples" / f"{name}.json").read_text())
    data["options"]["as_of_date"] = as_of
    return PlanRequest.model_validate(data)


def _json(plan: Plan) -> str:
    return json.dumps(plan.model_dump(mode="json"), sort_keys=True)


def test_same_input_same_as_of_identical_json() -> None:
    req = _req("intermediate_10k")
    a = planner.generate_plan(req, as_of_date=dt.date(2026, 9, 20))
    b = planner.generate_plan(req, as_of_date=dt.date(2026, 9, 20))
    assert isinstance(a, Plan) and isinstance(b, Plan)
    assert a.meta.as_of_date == dt.date(2026, 9, 20)
    assert _json(a) == _json(b)


def test_generated_at_derived_from_as_of_not_wall_clock() -> None:
    req = _req("beginner_half")
    plan = planner.generate_plan(req, as_of_date=dt.date(2026, 10, 2))
    assert isinstance(plan, Plan)
    assert plan.meta.as_of_date == dt.date(2026, 10, 2)
    assert plan.meta.generated_at == dt.datetime(2026, 10, 2, tzinfo=dt.UTC)


def test_as_of_drives_goal_too_soon() -> None:
    """Race 2026-12-12, 11-week 10k: OK on 09-26, too soon on 10-02."""
    req = _req("intermediate_10k")
    ok = planner.generate_plan(req, as_of_date=dt.date(2026, 9, 26))
    late = planner.generate_plan(req, as_of_date=dt.date(2026, 10, 2))
    assert isinstance(ok, Plan)
    assert ok.meta.as_of_date == dt.date(2026, 9, 26)
    assert isinstance(late, EngineError)
    assert late.code == ErrorCode.GOAL_TOO_SOON
    assert late.details["as_of_date"] == "2026-10-02"


def test_default_as_of_uses_system_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(planner, "_system_today", lambda: dt.date(2026, 10, 2))
    req = _req("intermediate_10k")
    assert req.options.as_of_date is None
    assert planner.resolve_as_of_date(req) == dt.date(2026, 10, 2)
    assert planner.resolve_as_of_date(req, dt.date(2026, 1, 1)) == dt.date(2026, 1, 1)


def test_options_as_of_date_echoed_and_deterministic() -> None:
    """options.as_of_date='2026-09-26' -> meta.as_of_date and identical JSON."""
    req = _req_with_options_as_of("intermediate_10k", "2026-09-26")
    assert req.options.as_of_date == dt.date(2026, 9, 26)
    a = planner.generate_plan(req)
    b = planner.generate_plan(req)
    assert isinstance(a, Plan) and isinstance(b, Plan)
    assert a.meta.as_of_date == dt.date(2026, 9, 26)
    assert b.meta.as_of_date == dt.date(2026, 9, 26)
    assert _json(a) == _json(b)


def test_kwarg_overrides_options_as_of_date() -> None:
    req = _req_with_options_as_of("beginner_half", "2026-09-26")
    plan = planner.generate_plan(req, as_of_date=dt.date(2026, 10, 2))
    assert isinstance(plan, Plan)
    assert plan.meta.as_of_date == dt.date(2026, 10, 2)
    assert plan.meta.generated_at == dt.datetime(2026, 10, 2, tzinfo=dt.UTC)
    assert planner.resolve_as_of_date(req, dt.date(2026, 10, 2)) == dt.date(2026, 10, 2)
    assert planner.resolve_as_of_date(req) == dt.date(2026, 9, 26)


def test_options_as_of_date_beats_system_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(planner, "_system_today", lambda: dt.date(2026, 10, 2))
    req = _req_with_options_as_of("intermediate_10k", "2026-09-20")
    assert planner.resolve_as_of_date(req) == dt.date(2026, 9, 20)


def test_datetime_kwarg_is_coerced_to_date() -> None:
    """datetime is a date subclass; keep a calendar date for arithmetic + JSON."""
    req = _req("intermediate_10k")
    instant = dt.datetime(2026, 9, 20, 15, 30, tzinfo=dt.UTC)
    assert planner.resolve_as_of_date(req, instant) == dt.date(2026, 9, 20)  # type: ignore[arg-type]


def test_no_race_date_window_follows_as_of() -> None:
    data = json.loads((ROOT / "examples" / "beginner_half.json").read_text())
    data["goal"]["race_date"] = None
    req = PlanRequest.model_validate(data)
    plan = planner.generate_plan(req, as_of_date=dt.date(2026, 10, 2))  # Friday
    assert isinstance(plan, Plan), plan
    assert plan.meta.start_date == dt.date(2026, 10, 5)  # next Monday
    assert plan.meta.as_of_date == dt.date(2026, 10, 2)


def test_no_hardcoded_dates_in_planner() -> None:
    src = (ROOT / "src" / "plan_engine" / "planner.py").read_text()
    assert "dt.date(2026" not in src
    assert "dt.datetime(2026" not in src
