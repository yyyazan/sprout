"""Time-of-day + greeting helpers (moved out of the Dash app, unchanged logic).

Single source of truth for "what part of the day is it" — drives both the
header greeting and the garden's sun/moon period. Server-local time.
"""
from __future__ import annotations

from datetime import datetime

_GREETINGS = {
    "morning": "Good morning",
    "afternoon": "Good afternoon",
    "evening": "Good evening",
    "night": "Good evening",
}


def time_of_day(hour: int | None = None) -> str:
    """Return one of "morning" | "afternoon" | "evening" | "night"."""
    if hour is None:
        hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def greeting_for(period: str) -> str:
    return _GREETINGS.get(period, "Welcome")
