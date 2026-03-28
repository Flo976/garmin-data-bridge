"""Parse Garmin API responses into generic health data payloads."""

from __future__ import annotations


def _get(responses: dict, key: str) -> dict | list | None:
    """Find a response by partial key match."""
    for url_fragment, data in responses.items():
        if key in url_fragment:
            return data
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

    def _sleep_min(key: str) -> int | None:
        val = sleep_dto.get(key)
        return val // 60 if val is not None else None

    return {
        "date": date_str,
        "steps": summary.get("totalSteps"),
        "calories": summary.get("totalKilocalories"),
        "restingHr": summary.get("restingHeartRate"),
        "stressAvg": stress.get("overallStressLevel"),
        "bodyBattery": max(bb_values) if bb_values else None,
        "hrvGarmin": hrv_last_night,
        "sleepScore": sleep_scores.get("overall"),
        "sleepTotalMin": _sleep_min("sleepTimeInSeconds"),
        "sleepDeepMin": _sleep_min("deepSleepSeconds"),
        "sleepRemMin": _sleep_min("remSleepSeconds"),
        "sleepLightMin": _sleep_min("lightSleepSeconds"),
        "sleepAwakeMin": _sleep_min("awakeSleepSeconds"),
        "vo2max": summary.get("vo2Max"),
    }


def parse_activity(act: dict) -> dict:
    """Parse a single Garmin activity into a generic activity payload."""
    def _int_or_none(val):
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


def parse_activities_list(responses: dict) -> list[dict]:
    """Parse activities list from intercepted responses."""
    activities_raw = _get(responses, "activitylist-service") or _get(responses, "activities")
    if not activities_raw:
        return []
    if isinstance(activities_raw, dict):
        activities_raw = activities_raw.get("activityList", activities_raw.get("activities", []))
    return [parse_activity(act) for act in activities_raw]
