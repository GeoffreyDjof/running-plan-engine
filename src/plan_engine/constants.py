"""Named coaching constants — copied 1:1 from docs/coaching-rules.md."""

from __future__ import annotations

# --- Progression volume ---
TARGET_WEEKLY_INCREASE_MIN = 0.05
TARGET_WEEKLY_INCREASE_MAX = 0.10
MAX_WEEKLY_INCREASE = 0.10
MAX_WEEKLY_INCREASE_HARD = 0.12
NO_CONSECUTIVE_LARGE_INCREASE_THRESHOLD = 0.10
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
