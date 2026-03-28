"""Parse activity list and detail data."""

from __future__ import annotations


def _int_or_none(val: int | float | None) -> int | None:
    return int(val) if val is not None else None


def parse_activity(act: dict) -> dict:
    """Parse a single Garmin activity into a generic activity payload."""
    return {
        "garminActivityId": str(act["activityId"]),
        "date": act.get("startTimeLocal"),
        "type": act.get("activityType", {}).get("typeKey", "other"),
        "name": act.get("activityName"),
        "durationS": int(act.get("duration", 0)),
        "distanceM": act.get("distance"),
        "elevationGainM": act.get("elevationGain"),
        "hrAvg": _int_or_none(act.get("averageHR")),
        "hrMax": _int_or_none(act.get("maxHR")),
        "calories": _int_or_none(act.get("calories")),
        "trainingEffectAerobic": act.get("aerobicTrainingEffect"),
        "trainingEffectAnaerobic": act.get("anaerobicTrainingEffect"),
        "vo2maxUpdate": act.get("vO2MaxValue"),
    }


def parse_activities_list(responses: dict, date_str: str | None = None) -> list[dict]:
    """Parse activities list from intercepted responses."""
    from src.parsers import _get

    activities_raw = _get(responses, "activitylist-service") or _get(responses, "activities")
    if not activities_raw:
        return []
    if isinstance(activities_raw, dict):
        activities_raw = activities_raw.get("activityList", activities_raw.get("activities", []))

    parsed = [parse_activity(act) for act in activities_raw]

    if date_str:
        parsed = [a for a in parsed if a.get("date", "")[:10] == date_str]

    return parsed
