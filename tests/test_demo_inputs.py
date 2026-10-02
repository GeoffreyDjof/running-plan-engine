"""P0 demo inputs: examples/demo/*.json parse and respect the 2026-10-02 window."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from plan_engine.models import PlanRequest
from plan_engine.planner import _select_template

DEMO_DIR = Path(__file__).resolve().parents[1] / "examples" / "demo"
AS_OF = dt.date(2026, 10, 2)

# Fallback if _select_template is awkward / returns None.
# Current v1 templates: 5k=10, 10k=11, half=12 (all levels).
_WEEKS_BY_GOAL_KM = {5.0: 10, 10.0: 11, 21.0975: 12}


def _demo_json_paths() -> list[Path]:
    return sorted(DEMO_DIR.glob("*.json"))


def _weeks_for(req: PlanRequest) -> int:
    tmpl = _select_template(req)
    if tmpl is not None:
        return int(tmpl.WEEKS)
    for km, weeks in _WEEKS_BY_GOAL_KM.items():
        if abs(req.goal.distance_km - km) <= 0.05:
            return weeks
    raise AssertionError(f"no template / WEEKS mapping for {req.goal.distance_km}")


@pytest.fixture(scope="module")
def demo_paths() -> list[Path]:
    paths = _demo_json_paths()
    assert paths, f"aucun JSON dans {DEMO_DIR}"
    return paths


def test_demo_folder_has_four_json_inputs(demo_paths: list[Path]) -> None:
    assert len(demo_paths) == 4
    names = {p.name for p in demo_paths}
    assert "demo_1_beginner_5k.json" in names
    assert "demo_2_intermediate_10k.json" in names
    assert "demo_4_undertrained_beginner_half.json" in names
    assert names & {
        "demo_3_advanced_half.json",
        "demo_3_intermediate_half.json",
    }


@pytest.mark.parametrize("path", _demo_json_paths(), ids=lambda p: p.name)
def test_demo_input_is_plan_request_dated_2026_10_02(path: Path) -> None:
    req = PlanRequest.model_validate_json(path.read_text(encoding="utf-8"))
    assert req.options.as_of_date == AS_OF


@pytest.mark.parametrize("path", _demo_json_paths(), ids=lambda p: p.name)
def test_demo_race_date_is_sunday_and_covers_template_weeks(path: Path) -> None:
    req = PlanRequest.model_validate_json(path.read_text(encoding="utf-8"))
    race = req.goal.race_date
    assert race is not None
    assert race.weekday() == 6  # Sunday
    assert req.options.as_of_date == AS_OF
    weeks = _weeks_for(req)
    assert (race - AS_OF).days >= weeks * 7 - 3
