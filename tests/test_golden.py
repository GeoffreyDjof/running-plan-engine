"""Goldens for examples/*_plan_generated.json.

The committed files are the current main output, regression included.
If this test fails, run `python scripts/regen_examples.py` and review the diff.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from plan_engine.models import PlanRequest
from plan_engine.planner import generate_plan

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
FALLBACK_AS_OF = dt.date(2026, 9, 26)
GOLDENS = sorted(EXAMPLES.glob("*_plan_generated.json"))


@pytest.mark.parametrize("golden", GOLDENS, ids=lambda p: p.name)
def test_generated_plan_matches_golden(golden: Path) -> None:
    src = EXAMPLES / golden.name.replace("_plan_generated.json", ".json")
    request = PlanRequest.model_validate_json(src.read_text(encoding="utf-8"))
    as_of = request.options.as_of_date or FALLBACK_AS_OF
    result = generate_plan(request, as_of_date=as_of)
    expected = json.loads(golden.read_text(encoding="utf-8"))
    actual = result.model_dump(mode="json")
    assert actual == expected, (
        f"{golden.name} is stale. Regenerate with "
        "`python scripts/regen_examples.py` and review the diff."
    )
