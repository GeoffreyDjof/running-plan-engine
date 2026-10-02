"""10k intermediate · 4 sessions/week · 11 weeks (within 10–12).

Volume targets are fractions of peak weekly km (clamped ≤ 60).
Session roles per week (4 slots: quality_day, easy_a, easy_b, long).
DomainCoach review target: easy≥0.75, ≤1 hard, ≤1 tempo, long≤38%,
deload every 3–4 load weeks, taper 7–10d, peak≤60.
"""

from __future__ import annotations

from typing import Any

TEMPLATE_ID = "intermediate_10k_4x_v1"
GOAL_KEY = "10k"
LEVEL = "intermediate"
SESSIONS_PER_WEEK = 4
WEEKS = 11
PEAK_WEEKLY_KM_CAP = 60.0
TARGET_PEAK_KM = 52.0  # under intermediate 10k cap
RACE_DISTANCE_KM = 10.0
DELOAD_FRACTION = 0.75
LONG_SHARE_LOAD = 0.30
LONG_SHARE_DELOAD = 0.28
LONG_SHARE_CAP = 0.37

# week_index (1-based) → spec
# roles use planner vocabulary; quality alternates tempo / intervals on load weeks
WEEK_SPECS: list[dict[str, Any]] = [
    # base
    {"week_index": 1, "phase": "base", "is_deload": False, "volume_frac": 0.70, "quality": None},
    {"week_index": 2, "phase": "base", "is_deload": False, "volume_frac": 0.76, "quality": "tempo"},
    {"week_index": 3, "phase": "base", "is_deload": False, "volume_frac": 0.82, "quality": "intervals"},
    {"week_index": 4, "phase": "base", "is_deload": True, "volume_frac": 0.70 * DELOAD_FRACTION, "quality": None},  # clamped vs last load in planner
    # development
    {"week_index": 5, "phase": "development", "is_deload": False, "volume_frac": 0.86, "quality": "tempo"},
    {"week_index": 6, "phase": "development", "is_deload": False, "volume_frac": 0.92, "quality": "intervals"},
    {"week_index": 7, "phase": "development", "is_deload": False, "volume_frac": 0.96, "quality": "tempo"},
    {"week_index": 8, "phase": "development", "is_deload": True, "volume_frac": 0.78 * DELOAD_FRACTION, "quality": None},
    # specific + taper + race
    {"week_index": 9, "phase": "specific", "is_deload": False, "volume_frac": 1.00, "quality": "intervals"},
    {"week_index": 10, "phase": "taper", "is_deload": False, "volume_frac": 0.55, "quality": "race_pace"},
    {"week_index": 11, "phase": "race", "is_deload": False, "volume_frac": 0.28, "quality": None, "include_race": True},
]


def week_specs() -> list[dict[str, Any]]:
    return [dict(s) for s in WEEK_SPECS]
