"""French display labels for goal distances and levels (messages, CLI)."""

from __future__ import annotations

GOAL_KEY_FR: dict[str, str] = {
    "5k": "5 km",
    "10k": "10 km",
    "half": "semi-marathon",
    "marathon": "marathon",
}
GOAL_KM_FR: dict[float, str] = {
    5.0: "5 km",
    10.0: "10 km",
    21.0975: "semi-marathon",
    42.195: "marathon",
}
LEVEL_FR: dict[str, str] = {
    "beginner": "débutant",
    "intermediate": "intermédiaire",
    "advanced": "confirmé",
}


def goal_key_fr(key: str) -> str:
    return GOAL_KEY_FR.get(key, key)


def level_fr(level: str) -> str:
    return LEVEL_FR.get(level, level)


def km_fr(value: float, decimals: int | None = None) -> str:
    """Format km with a French decimal comma: 9.4 -> '9,4', 10.0 -> '10'."""
    text = f"{value:.{decimals}f}" if decimals is not None else f"{value:g}"
    return text.replace(".", ",")
