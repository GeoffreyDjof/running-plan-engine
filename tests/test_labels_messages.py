"""French labels in refusal messages (no threshold or error code change)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from plan_engine import constants as C
from plan_engine.labels import GOAL_KEY_FR, LEVEL_FR, km_fr
from plan_engine.models import EngineError, ErrorCode, PlanRequest
from plan_engine.planner import generate_plan

ROOT = Path(__file__).resolve().parents[1]
AS_OF = "2026-09-26"


def _request(name: str, recent: list[float]) -> PlanRequest:
    data: dict[str, Any] = json.loads((ROOT / "examples" / f"{name}.json").read_text())
    data["athlete"]["recent_weekly_km"] = recent
    data.setdefault("options", {})["as_of_date"] = AS_OF
    return PlanRequest.model_validate(data)


def test_label_tables_cover_all_template_keys() -> None:
    assert set(C.RECENT_KM_MIN_FOR_GOAL) <= set(GOAL_KEY_FR)
    for levels in C.RECENT_KM_MIN_FOR_GOAL.values():
        assert set(levels) <= set(LEVEL_FR)
    assert GOAL_KEY_FR["half"] == "semi-marathon"
    assert LEVEL_FR["advanced"] == "confirmé"


def test_km_fr_uses_decimal_comma() -> None:
    assert km_fr(9.4, 1) == "9,4"
    assert km_fr(10.0) == "10"
    assert km_fr(15.0) == "15"


def test_goal_refusal_message_is_french_for_11_km() -> None:
    out = generate_plan(_request("beginner_half", [11, 10, 12, 11]))
    assert isinstance(out, EngineError)
    assert out.code == ErrorCode.VOLUME_TOO_LOW_FOR_GOAL
    assert out.message_fr.startswith(
        "Volume récent trop bas pour cet objectif : 11 km/sem, il faut au moins "
        "15 km/sem réguliers pour un semi-marathon niveau débutant."
    )
    assert "half" not in out.message_fr and "beginner" not in out.message_fr
    assert out.details["goal_distance_key"] == "half"  # codes unchanged
    assert out.details["level"] == "beginner"


def test_floor_refusal_message_is_french(monkeypatch: pytest.MonkeyPatch) -> None:
    # Unreachable with current constants (min goal km >= 10 -> cap >= 11);
    # lower the goal minimum only to exercise the floor message.
    patched = {k: {lvl: 0.0 for lvl in v} for k, v in C.RECENT_KM_MIN_FOR_GOAL.items()}
    monkeypatch.setattr(C, "RECENT_KM_MIN_FOR_GOAL", patched)
    ref = round(9.4 / C.START_VOLUME_MAX_RATIO, 4)
    out = generate_plan(_request("beginner_5k", [ref, ref, ref, ref]))
    assert isinstance(out, EngineError)
    assert out.code == ErrorCode.VOLUME_TOO_LOW_FOR_GOAL
    assert out.message_fr == (
        "Volume de départ trop bas : 9,4 km/sem, il faut au moins 10 km/sem "
        "réguliers pour démarrer un plan."
    )
