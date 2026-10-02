"""P0-8: demo CLI (formatting only, never edits the plan)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from plan_engine.cli import EXIT_BAD_INPUT, EXIT_OK, EXIT_REFUSED, build_request, run

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_plan_summary_in_french(capsys: pytest.CaptureFixture[str]) -> None:
    code = run([str(EXAMPLES / "beginner_10k.json"), "--as-of", "2026-09-26"])
    out = capsys.readouterr().out
    assert code == EXIT_OK
    assert "Plan 10 km — niveau débutant" in out
    assert "Allures (min/km)" in out
    assert "S1 " in out


def test_json_output_is_deterministic(capsys: pytest.CaptureFixture[str]) -> None:
    args = [str(EXAMPLES / "advanced_half.json"), "--as-of", "2026-09-26", "--json"]
    assert run(args) == EXIT_OK
    first = capsys.readouterr().out
    assert run(args) == EXIT_OK
    second = capsys.readouterr().out
    assert first == second
    assert "plan" in json.loads(first)


def test_refusal_exit_code_and_message(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    raw = json.loads((EXAMPLES / "beginner_10k.json").read_text(encoding="utf-8"))
    raw["goal"]["race_date"] = "2026-10-10"
    f = tmp_path / "too_soon.json"
    f.write_text(json.dumps(raw), encoding="utf-8")
    code = run([str(f), "--as-of", "2026-09-26"])
    out = capsys.readouterr().out
    assert code == EXIT_REFUSED
    assert out.startswith("Plan refusé — GOAL_TOO_SOON")


def test_refusal_json_is_typed_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    raw = json.loads((EXAMPLES / "beginner_10k.json").read_text(encoding="utf-8"))
    raw["goal"]["race_date"] = "2026-10-10"
    f = tmp_path / "too_soon.json"
    f.write_text(json.dumps(raw), encoding="utf-8")
    assert run([str(f), "--as-of", "2026-09-26", "--json"]) == EXIT_REFUSED
    err = json.loads(capsys.readouterr().out)
    assert err["code"] == "GOAL_TOO_SOON"
    assert err["message_fr"]


def test_bad_input_exit_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    f = tmp_path / "broken.json"
    f.write_text("{not json", encoding="utf-8")
    assert run([str(f)]) == EXIT_BAD_INPUT
    assert "Entrée invalide" in capsys.readouterr().err


def test_overrides_applied_without_mutating_input() -> None:
    raw = json.loads((EXAMPLES / "beginner_half.json").read_text(encoding="utf-8"))
    before = json.dumps(raw, sort_keys=True)
    req = build_request(raw, as_of=dt.date(2026, 9, 26), recent_km=[11, 10, 12, 11])
    assert req.athlete.recent_weekly_km == [11, 10, 12, 11]
    assert req.options.as_of_date == dt.date(2026, 9, 26)
    assert json.dumps(raw, sort_keys=True) == before


def test_recent_km_rejects_garbage() -> None:
    with pytest.raises(SystemExit):
        run([str(EXAMPLES / "beginner_10k.json"), "--recent-km", "onze"])
