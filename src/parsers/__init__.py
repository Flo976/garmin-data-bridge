"""Individual parsers for each Garmin data category."""
from __future__ import annotations


def _get(responses: dict[str, dict | list], key: str) -> dict | list | None:
    """Find a response by partial key match."""
    for url_fragment, data in responses.items():
        if key in url_fragment:
            return data
    return None


def has_data(daily: dict) -> bool:
    """Check if a daily summary has any non-null data worth uploading."""
    skip = {"date"}
    return any(v is not None for k, v in daily.items() if k not in skip)
