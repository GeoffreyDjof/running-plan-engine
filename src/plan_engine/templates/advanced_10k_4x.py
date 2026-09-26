"""10k advanced · 4 sessions/week · 11 weeks.

Bars (DomainCoach): long ≤40 %, peak ≤80, ≤1 QUALITY_HARD + ≤1 tempo / sem.
"""

from __future__ import annotations

from typing import Any

TEMPLATE_ID = "advanced_10k_4x_v1"
GOAL_KEY = "10k"
LEVEL = "advanced"
SESSIONS_PER_WEEK = 4
WEEKS = 11
PEAK_WEEKLY_KM_CAP = 80.0
TARGET_PEAK_KM = 70.0
RACE_DISTANCE_KM = 10.0
DELOAD_FRACTION = 0.75
LONG_SHARE_LOAD = 0.34
LONG_SHARE_DELOAD = 0.30
LONG_SHARE_CAP = 0.38  # margin under 0.40

WEEK_SPECS: list[dict[str, Any]] = [
    {"week_index": 1, "phase": "base", "is_deload": False, "volume_frac": 0.70, "quality": None},
    {"week_index": 2, "phase": "base", "is_deload": False, "volume_frac": 0.76, "quality": "tempo"},
    {"week_index": 3, "phase": "base", "is_deload": False, "volume_frac": 0.82, "quality": "intervals"},
    {"week_index": 4, "phase": "base", "is_deload": True, "volume_frac": 0.70 * DELOAD_FRACTION, "quality": None},
    {"week_index": 5, "phase": "development", "is_deload": False, "volume_frac": 0.86, "quality": "tempo"},
    {"week_index": 6, "phase": "development", "is_deload": False, "volume_frac": 0.92, "quality": "intervals"},
    {"week_index": 7, "phase": "development", "is_deload": False, "volume_frac": 0.96, "quality": "tempo"},
    {"week_index": 8, "phase": "development", "is_deload": True, "volume_frac": 0.78 * DELOAD_FRACTION, "quality": None},
    {"week_index": 9, "phase": "specific", "is_deload": False, "volume_frac": 1.00, "quality": "intervals"},
    {"week_index": 10, "phase": "taper", "is_deload": False, "volume_frac": 0.55, "quality": "race_pace"},
    {"week_index": 11, "phase": "race", "is_deload": False, "volume_frac": 0.28, "quality": None, "include_race": True},
]


def week_specs() -> list[dict[str, Any]]:
    return [dict(s) for s in WEEK_SPECS]
