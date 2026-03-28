"""Parse Garmin API responses into generic health data payloads."""

from __future__ import annotations


def _get(responses: dict[str, dict | list], key: str) -> dict | list | None:
    """Find a response by partial key match."""
    for url_fragment, data in responses.items():
        if key in url_fragment:
            return data
    return None


def _extract_training_readiness(raw: dict | list | None) -> float | None:
    """Extract training readiness score from various response shapes."""
    if raw is None:
        return None
    # Shape 1: dict with "score" key
    if isinstance(raw, dict):
        if "score" in raw:
            return raw["score"]
        # Shape 2: dict with nested list (e.g. {"entries": [{"score": 62}]})
        for key in ("entries", "days", "readiness"):
            items = raw.get(key, [])
            if isinstance(items, list) and items:
                first = items[0]
                if isinstance(first, dict) and "score" in first:
                    return first["score"]
    # Shape 3: list of daily readiness objects
    if isinstance(raw, list) and raw:
        first = raw[0]
        if isinstance(first, dict) and "score" in first:
            return first["score"]
    return None


def parse_daily_summary(responses: dict, date_str: str) -> dict:
    """Parse intercepted responses into a daily summary payload."""
    summary = _get(responses, "usersummary/daily") or {}
    sleep_raw = _get(responses, "dailySleepData") or {}
    stress = _get(responses, "dailyStress") or {}
    bb_raw = _get(responses, "bodybattery") or []
    hrv_raw = _get(responses, "hrv") or {}

    sleep_dto = sleep_raw.get("dailySleepDTO", {})
    sleep_scores = sleep_dto.get("sleepScores", {})

    bb_values = []
    if isinstance(bb_raw, list):
        for entry in bb_raw:
            for pair in entry.get("bodyBatteryValuesArray", []):
                if len(pair) >= 2 and pair[1] is not None:
                    bb_values.append(pair[1])

    hrv_summaries = hrv_raw.get("hrvSummaries", [])
    hrv_last_night = hrv_summaries[0].get("lastNightAvg") if hrv_summaries else None

    readiness_raw = _get(responses, "trainingReadiness")
    training_readiness = _extract_training_readiness(readiness_raw)

    # VO2max: try maxmet endpoint first, fallback to daily summary
    maxmet_raw = _get(responses, "maxmet") or []
    vo2max = None
    if isinstance(maxmet_raw, list) and maxmet_raw:
        vo2max = maxmet_raw[0].get("generic") or maxmet_raw[0].get("cycling")
    if vo2max is None:
        vo2max = summary.get("vo2Max")

    def _sleep_min(key: str) -> int | None:
        val = sleep_dto.get(key)
        return round(val / 60) if val is not None else None

    return {
        "date": date_str,
        "steps": summary.get("totalSteps"),
        "calories": summary.get("totalKilocalories"),
        "restingHr": summary.get("restingHeartRate"),
        "stressAvg": stress.get("overallStressLevel"),
        "bodyBattery": max(bb_values) if bb_values else None,
        "trainingReadiness": training_readiness,
        "hrvGarmin": hrv_last_night,
        "sleepScore": sleep_scores.get("overall"),
        "sleepTotalMin": _sleep_min("sleepTimeInSeconds"),
        "sleepDeepMin": _sleep_min("deepSleepSeconds"),
        "sleepRemMin": _sleep_min("remSleepSeconds"),
        "sleepLightMin": _sleep_min("lightSleepSeconds"),
        "sleepAwakeMin": _sleep_min("awakeSleepSeconds"),
        "vo2max": vo2max,
    }


def parse_activity(act: dict) -> dict:
    """Parse a single Garmin activity into a generic activity payload."""
    def _int_or_none(val: int | float | None) -> int | None:
        return int(val) if val is not None else None

    return {
        "garminActivityId": str(act["activityId"]),
        "date": act.get("startTimeLocal"),
        "type": act.get("activityType", {}).get("typeKey", "other"),
        "name": act.get("activityName"),
        "durationS": int(act.get("duration", 0)),
        "distanceM": act.get("distance"),
        "hrAvg": _int_or_none(act.get("averageHR")),
        "hrMax": _int_or_none(act.get("maxHR")),
        "calories": _int_or_none(act.get("calories")),
        "trainingEffectAerobic": act.get("aerobicTrainingEffect"),
        "trainingEffectAnaerobic": act.get("anaerobicTrainingEffect"),
        "vo2maxUpdate": act.get("vO2MaxValue"),
    }


def has_data(daily: dict) -> bool:
    """Check if a daily summary has any non-null data worth uploading."""
    skip = {"date"}
    return any(v is not None for k, v in daily.items() if k not in skip)


def parse_activities_list(responses: dict, date_str: str | None = None) -> list[dict]:
    """Parse activities list from intercepted responses.

    Args:
        responses: Captured API responses.
        date_str: If provided, only return activities matching this date (YYYY-MM-DD).
    """
    activities_raw = _get(responses, "activitylist-service") or _get(responses, "activities")
    if not activities_raw:
        return []
    if isinstance(activities_raw, dict):
        activities_raw = activities_raw.get("activityList", activities_raw.get("activities", []))

    parsed = [parse_activity(act) for act in activities_raw]

    if date_str:
        parsed = [a for a in parsed if a.get("date", "")[:10] == date_str]

    return parsed
