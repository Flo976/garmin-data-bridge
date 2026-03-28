"""Facade — assembles daily summary from individual parsers."""
from __future__ import annotations

from src.parsers import _get, has_data
from src.parsers.daily import parse_daily_core
from src.parsers.sleep import parse_sleep
from src.parsers.stress import parse_stress
from src.parsers.body_battery import parse_body_battery
from src.parsers.hrv import parse_hrv
from src.parsers.fitness import (
    parse_vo2max,
    parse_training_readiness,
    parse_training_status,
)
from src.parsers.activities import parse_activity, parse_activities_list

# Backward-compat alias (tests and callers imported this private name)
_extract_training_readiness = parse_training_readiness


def parse_daily_summary(responses: dict, date_str: str) -> dict:
    """Assemble daily summary from all parser modules."""
    summary = _get(responses, "usersummary/daily") or {}
    sleep_raw = _get(responses, "dailySleepData") or {}
    stress_raw = _get(responses, "dailyStress") or {}
    bb_raw = _get(responses, "bodybattery") or []
    hrv_raw = _get(responses, "hrv") or {}
    maxmet_raw = _get(responses, "maxmet") or []
    readiness_raw = _get(responses, "trainingReadiness")
    status_raw = _get(responses, "trainingStatus")

    result = {"date": date_str}
    result.update(parse_daily_core(summary))
    result.update(parse_sleep(sleep_raw))
    result.update(parse_stress(stress_raw))
    result.update(parse_body_battery(bb_raw))
    result.update(parse_hrv(hrv_raw))
    result["vo2max"] = parse_vo2max(maxmet_raw, summary)
    result["trainingReadiness"] = parse_training_readiness(readiness_raw)
    result.update(parse_training_status(status_raw))

    return result


# Re-export for backwards compatibility
__all__ = [
    "parse_daily_summary",
    "parse_activity",
    "parse_activities_list",
    "has_data",
    "_extract_training_readiness",
]
