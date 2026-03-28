"""Navigate Garmin Connect pages and intercept API responses."""

from __future__ import annotations

import json
import logging
from typing import Callable

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
    ("activitylist-service/activities", "activities"),
]


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


def sync_day(page: Page, date_str: str) -> dict[str, dict | list]:
    """Navigate daily pages and return all captured API responses."""
    captured: dict[str, dict | list] = {}
    handler = _make_response_handler(captured)
    page.on("response", handler)

    try:
        logger.info("Loading daily summary for %s", date_str)
        page.goto(
            f"https://connect.garmin.com/app/daily-summary/{date_str}",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        page.wait_for_load_state("networkidle", timeout=15_000)

        logger.info("Loading sleep data for %s", date_str)
        page.goto(
            f"https://connect.garmin.com/app/sleep/{date_str}",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        page.wait_for_load_state("networkidle", timeout=15_000)

        logger.info("Loading activities list")
        page.goto(
            "https://connect.garmin.com/app/activities",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        page.wait_for_load_state("networkidle", timeout=15_000)

    except Exception as e:
        logger.error("Navigation error during sync: %s", e)
    finally:
        page.remove_listener("response", handler)

    logger.info("Captured %d API responses", len(captured))
    return captured
