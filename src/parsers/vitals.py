"""Parse vitals data (respiration, SpO2, intensity minutes, floors)."""
from __future__ import annotations


def parse_respiration(raw: dict | None) -> dict:
    if not isinstance(raw, dict):
        return {"respirationAvgWaking": None, "respirationAvgSleep": None, "respirationMin": None, "respirationMax": None}
    return {
        "respirationAvgWaking": raw.get("avgWakingRespirationValue"),
        "respirationAvgSleep": raw.get("avgSleepRespirationValue"),
        "respirationMin": raw.get("lowestRespirationValue"),
        "respirationMax": raw.get("highestRespirationValue"),
    }


def parse_spo2(raw: dict | None) -> dict:
    if not isinstance(raw, dict):
        return {"spo2Avg": None, "spo2Min": None, "spo2Latest": None}
    return {
        "spo2Avg": raw.get("averageSPO2"),
        "spo2Min": raw.get("lowestSPO2"),
        "spo2Latest": raw.get("latestSPO2"),
    }


def parse_intensity_minutes(raw: dict | None) -> dict:
    if not isinstance(raw, dict):
        return {"intensityMinModerate": None, "intensityMinVigorous": None, "intensityMinWeeklyTotal": None}
    moderate = raw.get("weeklyModerate")
    vigorous = raw.get("weeklyVigorous")
    weekly_total = (moderate + vigorous) if moderate is not None and vigorous is not None else None
    return {
        "intensityMinModerate": raw.get("dailyModerate"),
        "intensityMinVigorous": raw.get("dailyVigorous"),
        "intensityMinWeeklyTotal": weekly_total,
    }


def parse_floors(raw: list | None) -> dict:
    if not isinstance(raw, list) or not raw:
        return {"floorsClimbed": None, "floorsDescended": None}
    total_up = sum(e.get("floorsAscended", 0) for e in raw if isinstance(e, dict))
    total_down = sum(e.get("floorsDescended", 0) for e in raw if isinstance(e, dict))
    return {
        "floorsClimbed": total_up or None,
        "floorsDescended": total_down or None,
    }
