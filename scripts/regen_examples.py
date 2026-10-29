"""Regenerate examples/*_plan_generated.json from the sibling request files.

Uses options.as_of_date when present, otherwise 2026-09-26 (historical examples).
Writes Plan or EngineError JSON. Re-run after a planner change, then review the diff.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

from plan_engine.models import PlanRequest
from plan_engine.planner import generate_plan

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
FALLBACK_AS_OF = dt.date(2026, 9, 26)


def _as_of(request: PlanRequest) -> dt.date:
    return request.options.as_of_date or FALLBACK_AS_OF


def regenerate() -> list[Path]:
    written: list[Path] = []
    for golden in sorted(EXAMPLES.glob("*_plan_generated.json")):
        src = EXAMPLES / golden.name.replace("_plan_generated.json", ".json")
        request = PlanRequest.model_validate_json(src.read_text(encoding="utf-8"))
        result = generate_plan(request, as_of_date=_as_of(request))
        golden.write_text(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n")
        written.append(golden)
    return written


def main() -> int:
    for path in regenerate():
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
