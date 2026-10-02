"""5k advanced · 4 sessions/week · 10 weeks.

Bars: long ≤40 %, peak ≤70 ; ≤1 hard + ≤1 tempo / sem ; taper 7–10d.
"""

from __future__ import annotations

from typing import Any

TEMPLATE_ID = "advanced_5k_4x_v1"
LEVEL = "advanced"
GOAL_KEY = "5k"
SESSIONS_PER_WEEK = 4
WEEKS = 10
PEAK_WEEKLY_KM_CAP = 70.0
TARGET_PEAK_KM = 58.0
DELOAD_FRACTION = 0.75
LONG_SHARE_LOAD = 0.34
LONG_SHARE_DELOAD = 0.30
LONG_SHARE_CAP = 0.38
RACE_DISTANCE_KM = 5.0

WEEK_SPECS: list[dict[str, Any]] = [
    {"week_index": 1, "phase": "base", "is_deload": False, "volume_frac": 0.70, "quality": None},
    {"week_index": 2, "phase": "base", "is_deload": False, "volume_frac": 0.78, "quality": "tempo"},
    {"week_index": 3, "phase": "base", "is_deload": False, "volume_frac": 0.84, "quality": "intervals"},
    {"week_index": 4, "phase": "base", "is_deload": True, "volume_frac": 0.70 * DELOAD_FRACTION, "quality": None},
    {"week_index": 5, "phase": "development", "is_deload": False, "volume_frac": 0.90, "quality": "tempo"},
    {"week_index": 6, "phase": "development", "is_deload": False, "volume_frac": 0.96, "quality": "intervals"},
    {"week_index": 7, "phase": "development", "is_deload": True, "volume_frac": 0.78 * DELOAD_FRACTION, "quality": None},
    {"week_index": 8, "phase": "specific", "is_deload": False, "volume_frac": 1.00, "quality": "intervals"},
    {"week_index": 9, "phase": "taper", "is_deload": False, "volume_frac": 0.55, "quality": "race_pace"},
    {"week_index": 10, "phase": "race", "is_deload": False, "volume_frac": 0.28, "quality": None, "include_race": True},
]


def week_specs() -> list[dict[str, Any]]:
    return [dict(s) for s in WEEK_SPECS]
