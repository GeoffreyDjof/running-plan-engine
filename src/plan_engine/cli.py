"""Demo CLI: PlanRequest JSON -> plan summary (fr) or typed refusal.

Usage::

    python -m plan_engine.cli examples/beginner_10k.json --as-of 2026-09-26
    python -m plan_engine.cli examples/beginner_half.json --recent-km 11,10,12,11
    python -m plan_engine.cli examples/advanced_5k.json --json > plan.json

Exit codes: 0 plan produced, 2 plan refused (EngineError), 1 bad input.
The CLI never edits the plan; it only formats what generate_plan returns.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from plan_engine.models import EngineError, Plan, PlanRequest
from plan_engine.planner import generate_plan

_ZONES = ("E", "M", "T", "I", "R")
_ZONE_FR = {
    "E": "Endurance",
    "M": "Allure marathon",
    "T": "Seuil",
    "I": "Intervalles",
    "R": "Répétitions",
}
_PHASE_FR = {
    "base": "base",
    "development": "développement",
    "specific": "spécifique",
    "taper": "affûtage",
    "race": "course",
}
_DAY_FR = {
    "mon": "lun",
    "tue": "mar",
    "wed": "mer",
    "thu": "jeu",
    "fri": "ven",
    "sat": "sam",
    "sun": "dim",
}
EXIT_OK = 0
EXIT_BAD_INPUT = 1
EXIT_REFUSED = 2


def _mmss(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}"


def _parse_recent_km(raw: str) -> list[float]:
    try:
        values = [float(x) for x in raw.split(",") if x.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"--recent-km attend des nombres séparés par des virgules : {raw!r}"
        ) from exc
    if not values or any(v < 0 for v in values):
        raise argparse.ArgumentTypeError("--recent-km : au moins une valeur, toutes ≥ 0")
    return values


def _parse_date(raw: str) -> dt.date:
    try:
        return dt.date.fromisoformat(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"date attendue au format AAAA-MM-JJ : {raw!r}") from exc


def build_request(
    raw: dict[str, Any],
    *,
    as_of: dt.date | None = None,
    recent_km: list[float] | None = None,
) -> PlanRequest:
    """Apply CLI overrides on the raw JSON, then validate the contract."""
    data = json.loads(json.dumps(raw))  # deep copy, JSON-safe
    if recent_km is not None:
        data.setdefault("athlete", {})["recent_weekly_km"] = recent_km
    if as_of is not None:
        data.setdefault("options", {})["as_of_date"] = as_of.isoformat()
    return PlanRequest.model_validate(data)


_GOAL_FR = {5.0: "5 km", 10.0: "10 km", 21.0975: "semi-marathon", 42.195: "marathon"}
_LEVEL_FR = {"beginner": "débutant", "intermediate": "intermédiaire", "advanced": "confirmé"}


def _goal_fr(distance_km: float) -> str:
    for km, label in _GOAL_FR.items():
        if abs(distance_km - km) <= 0.05:
            return label
    return f"{distance_km:g} km"


def format_plan(req: PlanRequest, plan: Plan) -> str:
    a, g, m = req.athlete, req.goal, plan.meta
    level = _LEVEL_FR.get(a.level.value, a.level.value)
    recent = ", ".join(f"{k:g}" for k in a.recent_weekly_km) or "—"
    lines = [
        (
            f"Plan {_goal_fr(g.distance_km)} — niveau {level} — {m.weeks} semaines "
            f"(début {m.start_date.isoformat()})"
        ),
        f"Km récents saisis : {recent}  ·  VDOT {m.vdot:.1f} (confiance {m.paces_confidence})",
    ]
    if m.as_of_date is not None:
        lines.append(f"Date de référence : {m.as_of_date.isoformat()}")
    lines.append("")
    lines.append("Allures (min/km) :")
    for key in _ZONES:
        z = getattr(plan.pace_zones, key)
        if z.range is not None:
            band = f"{_mmss(z.range.min_sec_per_km)}–{_mmss(z.range.max_sec_per_km)}"
        else:
            band = _mmss(z.pace_sec_per_km)
        lines.append(f"  {key}  {_ZONE_FR[key]:<16} {band}")
    lines.append("")
    lines.append("Semaines :")
    for w in plan.plan:
        actual = sum(s.total_km or 0.0 for s in w.sessions)
        tag = " (allègement)" if w.is_deload else ""
        days = "  ".join(
            f"{_DAY_FR.get(s.weekday.value, s.weekday.value)} {s.title}"
            for s in w.sessions
        )
        lines.append(
            f"  S{w.week_index:<2} {_PHASE_FR.get(w.phase.value, w.phase.value):<13}"
            f" {actual:5.1f} km{tag}"
        )
        lines.append(f"       {days}")
    for warn in m.warnings:
        lines.append(f"⚠ {warn.message_fr} [{warn.code}]")
    return "\n".join(lines)


def format_error(err: EngineError) -> str:
    lines = [f"Plan refusé — {err.code.value}", f"  {err.message_fr}"]
    details = err.details or {}
    rule = details.get("rule_id")
    if rule:
        lines.append(f"  Règle : {rule}")
    return "\n".join(lines)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="plan-engine",
        description="Génère un plan d'entraînement déterministe depuis un PlanRequest JSON.",
    )
    parser.add_argument("request", type=Path, help="Fichier PlanRequest JSON (ex. examples/beginner_10k.json)")
    parser.add_argument("--as-of", type=_parse_date, default=None, help="Date de référence AAAA-MM-JJ (défaut : options.as_of_date, sinon aujourd'hui)")
    parser.add_argument("--recent-km", type=_parse_recent_km, default=None, help="Remplace recent_weekly_km, ex. 11,10,12,11 (plus récente en dernier)")
    parser.add_argument("--json", action="store_true", help="Sortie JSON brute (plan ou erreur)")
    args = parser.parse_args(argv)

    try:
        raw = json.loads(args.request.read_text(encoding="utf-8"))
        req = build_request(raw, as_of=args.as_of, recent_km=args.recent_km)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"Entrée invalide : {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT

    result = generate_plan(req)
    if args.json:
        print(result.model_dump_json(indent=2))
    elif isinstance(result, EngineError):
        print(format_error(result))
    else:
        print(format_plan(req, result))
    return EXIT_REFUSED if isinstance(result, EngineError) else EXIT_OK


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
