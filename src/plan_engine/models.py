"""Pydantic v2 contracts for running-plan-engine (handoff §5 nested JSON)."""

from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Level(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class SessionKind(str, Enum):
    rest = "rest"
    easy = "easy"
    long = "long"
    strides = "strides"
    tempo = "tempo"
    cruise_intervals = "cruise_intervals"
    intervals = "intervals"
    reps = "reps"
    race_pace = "race_pace"
    recovery = "recovery"
    strength = "strength"
    cross = "cross"


class PlanPhase(str, Enum):
    base = "base"
    development = "development"
    specific = "specific"
    taper = "taper"
    race = "race"


class Weekday(str, Enum):
    """Weekday codes; Monday first."""

    mon = "mon"
    tue = "tue"
    wed = "wed"
    thu = "thu"
    fri = "fri"
    sat = "sat"
    sun = "sun"


class ErrorCode(str, Enum):
    """Top-level business error codes only (handoff §5.3).

    Validator-specific rule ids (QUALITY_BACK_TO_BACK, LONG_RUN_OVER_CEILING,
    VOLUME_JUMP_TOO_HIGH, SESSION_OVER_MAX_MINUTES, BEGINNER_AGGRESSIVE_REPS,
    INSUFFICIENT_EASY_RATIO, MISSING_TAPER, …) live in EngineError.details
    under code=VALIDATION_FAILED (or INJURY_BLOCKS_QUALITY when injury+quality).
    Promote a rule id to ErrorCode only via ADR.
    """

    INSUFFICIENT_AVAILABILITY = "INSUFFICIENT_AVAILABILITY"
    GOAL_TOO_SOON = "GOAL_TOO_SOON"
    VOLUME_TOO_LOW_FOR_GOAL = "VOLUME_TOO_LOW_FOR_GOAL"
    BENCHMARK_IMPLAUSIBLE = "BENCHMARK_IMPLAUSIBLE"
    INJURY_BLOCKS_QUALITY = "INJURY_BLOCKS_QUALITY"
    VALIDATION_FAILED = "VALIDATION_FAILED"


# Known validator rule_id strings for details (not ErrorCode members).
VALIDATOR_RULE_IDS: frozenset[str] = frozenset(
    {
        "QUALITY_BACK_TO_BACK",
        "LONG_RUN_OVER_CEILING",
        "VOLUME_JUMP_TOO_HIGH",
        "SESSION_OVER_MAX_MINUTES",
        "BEGINNER_AGGRESSIVE_REPS",
        "INSUFFICIENT_EASY_RATIO",
        "MISSING_TAPER",
    }
)

PaceZoneKey = Literal["E", "M", "T", "I", "R"]
PacesConfidence = Literal["high", "medium", "low"]
StructureBlockRole = Literal["warmup", "main", "cooldown", "other"]
Sex = Literal["female", "male", "other"]


# ---------------------------------------------------------------------------
# Input (§5.1)
# ---------------------------------------------------------------------------


class DayAvailability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weekday: Weekday
    max_minutes: int = Field(ge=0, description="0 = unavailable that day")


class AthleteConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    injuries: list[str] = Field(default_factory=list)
    no_track: bool = False
    prefers_time_based: bool = False


class Athlete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    age: int | None = Field(default=None, ge=1, le=120)
    sex: Sex | None = None
    experience_years: float | None = Field(default=None, ge=0)
    level: Level
    recent_weekly_km: list[float] = Field(
        default_factory=list,
        description="Last N weeks of volume; newest last (handoff: typically 4)",
    )
    longest_run_km_last_4w: float | None = Field(default=None, ge=0)
    availability: list[DayAvailability] = Field(min_length=1)
    constraints: AthleteConstraints = Field(default_factory=AthleteConstraints)

    @field_validator("recent_weekly_km")
    @classmethod
    def _volumes_non_negative(cls, v: list[float]) -> list[float]:
        if any(x < 0 for x in v):
            raise ValueError("recent_weekly_km values must be >= 0")
        return v

    @model_validator(mode="after")
    def _unique_weekdays(self) -> Athlete:
        days = [d.weekday for d in self.availability]
        if len(days) != len(set(days)):
            raise ValueError("availability weekdays must be unique")
        return self


class Benchmark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distance_km: float = Field(gt=0)
    time_sec: int = Field(gt=0)
    date: dt.date | None = None
    is_estimate: bool = False


class Goal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distance_km: float = Field(
        gt=0,
        description="Canonical v1: 5, 10, 21.0975, 42.195",
    )
    race_date: dt.date | None = None
    target_time_sec: int | None = Field(default=None, gt=0)


class Options(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sessions_per_week: int = Field(ge=3, le=6)
    include_strength: bool = False
    units: Literal["metric"] = "metric"
    language: Literal["fr"] = "fr"


class PlanRequest(BaseModel):
    """Nested input contract — handoff §5.1."""

    model_config = ConfigDict(extra="forbid")

    athlete: Athlete
    benchmark: Benchmark | None = None
    goal: Goal
    options: Options


# ---------------------------------------------------------------------------
# Output (§5.2)
# ---------------------------------------------------------------------------


class PaceZoneDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pace_sec_per_km: int = Field(gt=0, description="Seconds per km (E/M/T/I/R)")
    label: str


class PaceZones(BaseModel):
    """Daniels-style zones keyed E / M / T / I / R."""

    model_config = ConfigDict(extra="forbid")

    E: PaceZoneDetail
    M: PaceZoneDetail
    T: PaceZoneDetail
    I: PaceZoneDetail
    R: PaceZoneDetail


class StructureBlock(BaseModel):
    """WU / main / CD (or other) block inside a session."""

    model_config = ConfigDict(extra="forbid")

    block: StructureBlockRole
    duration_min: float | None = Field(default=None, ge=0)
    distance_km: float | None = Field(default=None, ge=0)
    zone: PaceZoneKey | None = None


class Session(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    weekday: Weekday
    date: dt.date
    kind: SessionKind
    title: str
    structure: list[StructureBlock] = Field(default_factory=list)
    total_km: float | None = Field(default=None, ge=0)
    total_minutes_est: float = Field(ge=0)
    load: str | None = None
    notes_fr: str = ""


class WeekPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    week_index: int = Field(ge=1)
    phase: PlanPhase
    target_km: float = Field(ge=0)
    is_deload: bool = False
    sessions: list[Session] = Field(default_factory=list)


class PlanMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine_version: str
    generated_at: dt.datetime
    method: str = "vdot_templates_v1"
    vdot: float = Field(gt=0)
    paces_confidence: PacesConfidence
    start_date: dt.date
    weeks: int = Field(ge=1)
    warnings: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """Nested output contract — handoff §5.2."""

    model_config = ConfigDict(extra="forbid")

    meta: PlanMeta
    pace_zones: PaceZones
    plan: list[WeekPlan]


class EngineError(BaseModel):
    """Typed business / validation failure — never return an invalid Plan.

    For validator failures use code=VALIDATION_FAILED (or INJURY_BLOCKS_QUALITY)
    and put structured info in details, e.g.::

        details = {
            "rule_id": "QUALITY_BACK_TO_BACK",
            "broken_rules": ["QUALITY_BACK_TO_BACK", "INSUFFICIENT_EASY_RATIO"],
        }
    """

    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message_fr: str
    details: dict[str, Any] = Field(default_factory=dict)


PlanResult: TypeAlias = Plan | EngineError
