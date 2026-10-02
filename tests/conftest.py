"""Shared pytest config.

Example requests were authored against reference date 2026-09-26. Pin the
engine's "today" so the suite does not drift with the wall clock (P0-7).
"""

from __future__ import annotations

import datetime as dt

import pytest

from plan_engine import planner

REFERENCE_AS_OF = dt.date(2026, 9, 26)


@pytest.fixture(autouse=True)
def _pin_engine_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(planner, "_system_today", lambda: REFERENCE_AS_OF)
