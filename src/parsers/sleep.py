"""Parse sleep data."""

from __future__ import annotations


def parse_sleep(sleep_raw: dict) -> dict:
    """Extract sleep metrics from dailySleepData response."""
    sleep_dto = sleep_raw.get("dailySleepDTO", {})
    sleep_scores = sleep_dto.get("sleepScores", {})

    def _sleep_min(key: str) -> int | None:
        val = sleep_dto.get(key)
        return round(val / 60) if val is not None else None

    return {
        "sleepScore": sleep_scores.get("overall"),
        "sleepTotalMin": _sleep_min("sleepTimeInSeconds"),
        "sleepDeepMin": _sleep_min("deepSleepSeconds"),
        "sleepRemMin": _sleep_min("remSleepSeconds"),
        "sleepLightMin": _sleep_min("lightSleepSeconds"),
        "sleepAwakeMin": _sleep_min("awakeSleepSeconds"),
    }
