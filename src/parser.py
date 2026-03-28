"""Facade — assembles daily summary from individual parsers."""
from __future__ import annotations

from src.parsers import _get, has_data
from src.parsers.daily import parse_daily_core
from src.parsers.sleep import parse_sleep
from src.parsers.stress import parse_stress
from src.parsers.body_battery import parse_body_battery, parse_body_battery_events
from src.parsers.hrv import parse_hrv
from src.parsers.fitness import (
    parse_vo2max,
    parse_training_readiness,
    parse_training_status,
    parse_endurance_score,
    parse_hill_score,
    parse_fitness_age,
    parse_race_predictions,
)
from src.parsers.vitals import parse_respiration, parse_spo2, parse_intensity_minutes, parse_floors
from src.parsers.body_comp import parse_body_composition
from src.parsers.records import parse_personal_records
from src.parsers.activities import parse_activity, parse_activities_list

# Backwards compatibility alias
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
    respiration_raw = _get(responses, "respiration")
    spo2_raw = _get(responses, "spo2")
    im_raw = _get(responses, "intensityMinutes")
    floors_raw = _get(responses, "floors")
    endurance_raw = _get(responses, "enduranceScore")
    hill_raw = _get(responses, "hillScore")
    fitness_age_raw = _get(responses, "fitnessAge")
    race_raw = _get(responses, "racePredictions")

    result = {"date": date_str}
    result.update(parse_daily_core(summary))
    result.update(parse_sleep(sleep_raw))
    result.update(parse_stress(stress_raw))
    result.update(parse_body_battery(bb_raw))
    result.update(parse_hrv(hrv_raw))
    result.update(parse_respiration(respiration_raw))
    result.update(parse_spo2(spo2_raw))
    result.update(parse_intensity_minutes(im_raw))
    result.update(parse_floors(floors_raw))
    result.update(parse_training_status(status_raw))
    result.update(parse_race_predictions(race_raw))
    result["vo2max"] = parse_vo2max(maxmet_raw, summary)
    result["trainingReadiness"] = parse_training_readiness(readiness_raw)
    result["enduranceScore"] = parse_endurance_score(endurance_raw)
    result["hillScore"] = parse_hill_score(hill_raw)
    result["fitnessAge"] = parse_fitness_age(fitness_age_raw)

    return result


def parse_body_comp(responses: dict) -> dict | None:
    """Parse body composition from intercepted responses."""
    raw = _get(responses, "bodyComposition")
    if raw is None:
        return None
    result = parse_body_composition(raw)
    return result if any(v is not None for v in result.values()) else None


def parse_records(responses: dict) -> list[dict]:
    """Parse personal records from intercepted responses."""
    raw = _get(responses, "personalRecords")
    return parse_personal_records(raw)


def parse_bb_events(responses: dict) -> list[dict]:
    """Parse body battery events from intercepted responses."""
    raw = _get(responses, "bodyBatteryEvents")
    return parse_body_battery_events(raw)


__all__ = [
    "parse_daily_summary",
    "parse_activity",
    "parse_activities_list",
    "parse_body_comp",
    "parse_records",
    "parse_bb_events",
    "has_data",
    "_extract_training_readiness",
]
