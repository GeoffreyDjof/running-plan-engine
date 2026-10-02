"""Named coaching constants — copied 1:1 from docs/coaching-rules.md."""

from __future__ import annotations

# --- Progression volume ---
TARGET_WEEKLY_INCREASE_MIN = 0.05
TARGET_WEEKLY_INCREASE_MAX = 0.10
MAX_WEEKLY_INCREASE = 0.10
MAX_WEEKLY_INCREASE_HARD = 0.12
NO_CONSECUTIVE_LARGE_INCREASE_THRESHOLD = 0.10
# Planner guard on *actual* load→load km (slack under R01/R02 for rounding)
LOAD_STEP_ACTUAL_MAX = 0.09
DELOAD_FRACTION_MIN = 0.70
DELOAD_FRACTION_MAX = 0.80
DELOAD_EVERY_WEEKS_MIN = 3
DELOAD_EVERY_WEEKS_MAX = 4

# --- Polarization / intensity ---
EASY_SHARE_MIN_LOAD_WEEK = 0.75
EASY_SHARE_TARGET = 0.80
MAX_VERY_HARD_QUALITY_PER_WEEK = 1
MAX_TEMPO_QUALITY_PER_WEEK = 1
FORBID_HARD_QUALITY_CONSECUTIVE_DAYS = True
DAY_AFTER_LONG_ALLOWED = ("easy", "recovery", "rest")

# --- Long run share caps by level ---
LONG_RUN_SHARE_MAX_BEGINNER = 0.35
LONG_RUN_SHARE_MAX_INTERMEDIATE = 0.38
LONG_RUN_SHARE_MAX_ADVANCED = 0.40
LONG_RUN_SHARE_MAX = {
    "beginner": LONG_RUN_SHARE_MAX_BEGINNER,
    "intermediate": LONG_RUN_SHARE_MAX_INTERMEDIATE,
    "advanced": LONG_RUN_SHARE_MAX_ADVANCED,
}
INJURY_LONG_RUN_SHARE_CAP = 0.30

# --- Session duration ---
SESSION_MUST_RESPECT_MAX_MINUTES = True
STRENGTH_MAX_MINUTES = 30
BEGINNER_QUALITY_TEMPO_MAX_PER_PLAN = 1

# --- Taper days by distance ---
TAPER_DAYS = {
    "5k": (7, 10),
    "10k": (7, 10),
    "half": (10, 14),
    "marathon": (14, 21),
}

# --- Injury ---
INJURY_BLOCKS_QUALITY_HARD = True
INJURY_BLOCKS_QUALITY_TEMPO = True

# --- Peak weekly km max: PEAK_WEEKLY_KM_MAX[level][distance] ---
PEAK_WEEKLY_KM_MAX = {
    "beginner": {"5k": 35, "10k": 40, "half": 45, "marathon": 50},
    "intermediate": {"5k": 50, "10k": 60, "half": 65, "marathon": 75},
    "advanced": {"5k": 70, "10k": 80, "half": 90, "marathon": 110},
}

# --- Benchmark plausible bounds (seconds) ---
BENCHMARK_BOUNDS_SEC = {
    "5k": (750, 3600),
    "10k": (1560, 7200),
    "half": (3480, 14400),
    "marathon": (7500, 28800),
}

# --- Kind classes ---
QUALITY_HARD = frozenset({"intervals", "reps"})
QUALITY_TEMPO = frozenset({"tempo", "cruise_intervals", "race_pace"})
EASY_FAMILY = frozenset({"easy", "recovery", "long", "cross"})
QUALITY_ANY = QUALITY_HARD | QUALITY_TEMPO

# --- VDOT / paces (coaching-rules §3.7) ---
VDOT_ANCHOR_DISTANCE = "5k"
VDOT_ANCHOR_TIME_SEC = 1200
VDOT_ANCHOR_EXPECTED = 51.0
VDOT_TOLERANCE_ABS = 0.5
PACE_ZONE_METHOD = "daniels_vdot_tables"
PACE_OUTPUT_UNIT = "sec_per_km"
PACE_ZONES_REQUIRED = ("E", "M", "T", "I", "R")

# Daniels regression under-reads published tables (~49.8 vs 51 for 5k@20:00).
# Scale so the published anchor matches coaching-rules; document in paces.py.
VDOT_TABLE_SCALE = 51.0 / 49.806233428066335

# % of VDOT (VO2) used to derive training paces (Daniels-style single points).
# Chosen to approximate published VDOT-51 pace table (sec/km order E>M>T>I, I>=R).
ZONE_VO2_FRACTION = {
    "E": 0.65,
    "M": 0.82,
    "T": 0.88,
    "I": 0.98,
    "R": 1.07,
}

ZONE_LABELS = {
    "E": "Easy",
    "M": "Marathon",
    "T": "Threshold",
    "I": "Interval",
    "R": "Repetition",
}

# Canonical goal/benchmark distance_km → key used in BENCHMARK_BOUNDS_SEC
DISTANCE_KM_TO_KEY = {
    5.0: "5k",
    10.0: "10k",
    21.0975: "half",
    42.195: "marathon",
}
DISTANCE_KEY_TO_M = {
    "5k": 5000.0,
    "10k": 10000.0,
    "half": 21097.5,
    "marathon": 42195.0,
}

# --- Start volume from real recent km (coaching-rules §3.8, P0-1 / P0-4) ---
# ref_km = min(median(last START_REF_WEEKS weeks), max(last START_REF_RECENT_WEEKS))
START_REF_WEEKS = 4
START_REF_RECENT_WEEKS = 2
# Week 1 volume <= START_VOLUME_MAX_RATIO * ref_km (same as max weekly increase).
START_VOLUME_MAX_RATIO = 1.10
# Below this week-1 cap we refuse; the engine never raises volume to a floor.
START_VOLUME_FLOOR_KM = 10.0
# Minimum real recent km/week to accept a goal: RECENT_KM_MIN_FOR_GOAL[distance][level]
RECENT_KM_MIN_FOR_GOAL = {
    "5k": {"beginner": 10.0, "intermediate": 16.0, "advanced": 26.0},
    "10k": {"beginner": 13.0, "intermediate": 20.0, "advanced": 29.0},
    "half": {"beginner": 15.0, "intermediate": 20.0, "advanced": 29.0},
}

# --- P0-6 pace ranges (DomainCoach coaching-rules §3.9) ---------------------
# (fast_side_pct, slow_side_pct) around the central zone pace; wider on the
# slow side ("au doute, plus lent"). Bounds rounded to the nearest 5 s, then
# widened only if needed so the band contains the central pace.
PACE_RANGE_PCT: dict[str, tuple[float, float]] = {
    "E": (0.03, 0.08),
    "M": (0.01, 0.03),
    "T": (0.01, 0.02),
    "I": (0.01, 0.02),
    "R": (0.01, 0.02),
}
PACE_RANGE_ROUND_SEC = 5
