"""Half advanced · 4 sessions/week · 12 weeks.

Bars: peak ≤90 ; taper 10–14d ; long sous plafond level.
"""

from __future__ import annotations

from typing import Any

TEMPLATE_ID = "advanced_half_4x_v1"
LEVEL = "advanced"
GOAL_KEY = "half"
SESSIONS_PER_WEEK = 4
WEEKS = 12
PEAK_WEEKLY_KM_CAP = 90.0
TARGET_PEAK_KM = 78.0
RACE_DISTANCE_KM = 21.0975
DELOAD_FRACTION = 0.75
LONG_SHARE_LOAD = 0.34
LONG_SHARE_DELOAD = 0.3
LONG_SHARE_CAP = 0.38

WEEK_SPECS: list[dict[str, Any]] = [{"week_index": 1, "phase": "base", "is_deload": False, "volume_frac": 0.62, "quality": None}, {"week_index": 2, "phase": "base", "is_deload": False, "volume_frac": 0.68, "quality": "tempo"}, {"week_index": 3, "phase": "base", "is_deload": False, "volume_frac": 0.74, "quality": "intervals"}, {"week_index": 4, "phase": "base", "is_deload": True, "volume_frac": 0.51, "quality": None}, {"week_index": 5, "phase": "development", "is_deload": False, "volume_frac": 0.8, "quality": "tempo"}, {"week_index": 6, "phase": "development", "is_deload": False, "volume_frac": 0.86, "quality": "intervals"}, {"week_index": 7, "phase": "development", "is_deload": False, "volume_frac": 0.92, "quality": "tempo"}, {"week_index": 8, "phase": "development", "is_deload": True, "volume_frac": 0.585, "quality": None}, {"week_index": 9, "phase": "specific", "is_deload": False, "volume_frac": 0.96, "quality": "intervals"}, {"week_index": 10, "phase": "specific", "is_deload": False, "volume_frac": 1.0, "quality": "tempo"}, {"week_index": 11, "phase": "taper", "is_deload": False, "volume_frac": 0.55, "quality": "race_pace"}, {"week_index": 12, "phase": "race", "is_deload": False, "volume_frac": 0.3, "quality": None, "include_race": True}]


def week_specs() -> list[dict[str, Any]]:
    return [dict(s) for s in WEEK_SPECS]
