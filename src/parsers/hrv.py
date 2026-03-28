"""Parse HRV data."""
from __future__ import annotations


def parse_hrv(hrv_raw: dict) -> dict:
    """Extract HRV metrics from hrv-service response."""
    hrv_summaries = hrv_raw.get("hrvSummaries", [])
    last_night = hrv_summaries[0].get("lastNightAvg") if hrv_summaries else None
    baseline = hrv_summaries[0].get("baseline", {}) if hrv_summaries else {}
    return {
        "hrvGarmin": last_night,
        "hrvWeeklyAvg": hrv_summaries[0].get("weeklyAvg") if hrv_summaries else None,
        "hrvBaseline": baseline.get("lowUpper") if baseline else None,
    }
