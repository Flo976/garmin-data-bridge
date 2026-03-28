"""Parse personal records."""

from __future__ import annotations


def parse_personal_records(raw: list | None) -> list[dict]:
    if not isinstance(raw, list):
        return []
    result = []
    for pr in raw:
        if not isinstance(pr, dict):
            continue
        result.append(
            {
                "type": pr.get("prTypeLabelKey"),
                "value": pr.get("value"),
                "date": pr.get("prStartTimeGMTFormatted"),
                "activityId": pr.get("activity", {}).get("activityId"),
            }
        )
    return result
