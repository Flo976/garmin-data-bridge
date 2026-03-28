"""Parse daily summary (steps, calories, resting HR)."""

from __future__ import annotations


def parse_daily_core(summary: dict) -> dict:
    """Extract core daily metrics from usersummary response."""
    return {
        "steps": summary.get("totalSteps"),
        "calories": summary.get("totalKilocalories"),
        "restingHr": summary.get("restingHeartRate"),
        "floorsClimbed": summary.get("floorsAscended"),
    }
