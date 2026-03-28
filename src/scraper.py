"""Navigate Garmin Connect pages and intercept API responses."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Callable

try:
    from patchright.sync_api import Page, Response
except ImportError:
    from playwright.sync_api import Page, Response

logger = logging.getLogger(__name__)

_CAPTURE_PATTERNS: list[tuple[str, str]] = [
    ("usersummary-service/usersummary/daily", "usersummary/daily"),
    ("wellness-service/wellness/dailySleepData", "dailySleepData"),
    ("wellness-service/wellness/dailyHeartRate", "dailyHeartRate"),
    ("wellness-service/wellness/dailyStress", "dailyStress"),
    ("bodybattery-service/bodybattery", "bodybattery"),
    ("hrv-service/hrv", "hrv"),
    ("metrics-service/metrics/maxmet/daily", "maxmet"),
    ("fitnessStats-service/trainingReadiness", "trainingReadiness"),
    ("activitylist-service/activities", "activities"),
]


@dataclass
class SyncResult:
    """Holds captured API responses and tracks which pages loaded successfully."""
    responses: dict[str, dict | list] = field(default_factory=dict)
    pages_loaded: set[str] = field(default_factory=set)
    pages_failed: set[str] = field(default_factory=set)

    @property
    def is_complete(self) -> bool:
        """True if all attempted pages loaded without error."""
        return len(self.pages_failed) == 0 and len(self.pages_loaded) > 0


def _make_response_handler(captured: dict[str, dict | list]) -> Callable:
    """Create a response handler that captures matched API responses."""
    def handler(response: Response) -> None:
        if response.status != 200:
            return
        url = response.url
        for pattern, key in _CAPTURE_PATTERNS:
            if pattern in url:
                try:
                    data = response.json()
                    captured[key] = data
                    logger.debug("Captured %s (%d bytes)", key, len(json.dumps(data)))
                except Exception:
                    logger.debug("Non-JSON response for %s, skipping", key)
                break

        if "graphql-gateway/graphql" in url:
            try:
                data = response.json()
                gql_data = data.get("data", {})
                for gql_key in gql_data:
                    captured[f"graphql/{gql_key}"] = gql_data[gql_key]
                    logger.debug("Captured GraphQL: %s", gql_key)
            except Exception:
                pass

    return handler


def _navigate(page: Page, url: str, result: SyncResult, label: str) -> None:
    """Navigate to a page and track success/failure."""
    try:
        logger.info("Loading %s", label)
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_load_state("networkidle", timeout=15_000)
        result.pages_loaded.add(label)
    except Exception as e:
        logger.warning("Page load failed for %s: %s", label, e)
        result.pages_failed.add(label)


def sync_day(page: Page, date_str: str, include_activities: bool = True) -> SyncResult:
    """Navigate daily pages and return all captured API responses.

    Args:
        page: The browser page to use.
        date_str: Date to sync (YYYY-MM-DD).
        include_activities: Whether to load the activities page.
            Set to False during backfill to avoid re-uploading.
    """
    result = SyncResult()
    handler = _make_response_handler(result.responses)
    page.on("response", handler)

    try:
        _navigate(
            page,
            f"https://connect.garmin.com/app/daily-summary/{date_str}",
            result,
            f"daily summary ({date_str})",
        )

        _navigate(
            page,
            f"https://connect.garmin.com/app/sleep/{date_str}",
            result,
            f"sleep ({date_str})",
        )

        if include_activities:
            _navigate(
                page,
                "https://connect.garmin.com/app/activities",
                result,
                "activities",
            )

    finally:
        page.remove_listener("response", handler)

    logger.info(
        "Captured %d API responses (pages: %d ok, %d failed)",
        len(result.responses),
        len(result.pages_loaded),
        len(result.pages_failed),
    )
    return result
