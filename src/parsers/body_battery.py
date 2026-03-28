"""Parse body battery data."""
from __future__ import annotations


def parse_body_battery(bb_raw: list | dict) -> dict:
    """Extract body battery max/min from bodybattery response."""
    bb_values = []
    if isinstance(bb_raw, list):
        for entry in bb_raw:
            for pair in entry.get("bodyBatteryValuesArray", []):
                if len(pair) >= 2 and pair[1] is not None:
                    bb_values.append(pair[1])
    return {
        "bodyBattery": max(bb_values) if bb_values else None,
        "bodyBatteryMin": min(bb_values) if bb_values else None,
    }


def parse_body_battery_events(events_raw: dict | list) -> list[dict]:
    """Extract body battery drain/charge events."""
    if isinstance(events_raw, dict):
        events_raw = events_raw.get("events", events_raw.get("bodyBatteryEvents", []))
    if not isinstance(events_raw, list):
        return []
    result = []
    for ev in events_raw:
        if not isinstance(ev, dict):
            continue
        result.append({
            "eventType": ev.get("eventType"),
            "startGMT": ev.get("startTimestampGMT"),
            "endGMT": ev.get("endTimestampGMT"),
            "bodyBatteryImpact": ev.get("bodyBatteryImpact"),
            "activityName": ev.get("activityName"),
        })
    return result
