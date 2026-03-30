"""Navigate Garmin Connect pages and intercept API responses."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Callable

try:
    from patchright.sync_api import BrowserContext, Page, Response
except ImportError:
    from playwright.sync_api import BrowserContext, Page, Response

logger = logging.getLogger(__name__)

# All available pages that can be scraped
ALL_PAGES = {"daily", "sleep", "training-status", "body-composition", "activities", "personal-records"}
DEFAULT_PAGES = {"daily", "sleep", "training-status", "body-composition", "activities", "personal-records"}

_CAPTURE_PATTERNS: list[tuple[str, str]] = [
    # Daily summary page
    ("usersummary-service/usersummary/daily", "usersummary/daily"),
    ("wellness-service/wellness/dailyStress", "dailyStress"),
    ("bodybattery-service/bodybattery", "bodybattery"),
    ("wellness-service/wellness/daily/respiration", "respiration"),
    ("wellness-service/wellness/daily/spo2", "spo2"),
    ("wellness-service/wellness/daily/im", "intensityMinutes"),
    ("wellness-service/wellness/floorsChartData/daily", "floors"),
    ("wellness-service/wellness/bodyBattery/events", "bodyBatteryEvents"),
    # Sleep page
    ("wellness-service/wellness/dailySleepData", "dailySleepData"),
    ("hrv-service/hrv", "hrv"),
    # Fitness stats pages
    ("metrics-service/metrics/maxmet/daily", "maxmet"),
    ("fitnessStats-service/trainingReadiness", "trainingReadiness"),
    ("metrics-service/metrics/trainingstatus/aggregated", "trainingStatus"),
    ("metrics-service/metrics/endurancescore", "enduranceScore"),
    ("metrics-service/metrics/hillscore", "hillScore"),
    ("metrics-service/metrics/racepredictions", "racePredictions"),
    ("fitnessage-service/fitnessage", "fitnessAge"),
    # Body composition page
    ("weight-service/weight/dateRange", "bodyComposition"),
    ("weight-service/weight/range", "bodyComposition"),
    # Activities page
    ("activitylist-service/activities", "activities"),
    # Personal records page
    ("personalrecord-service/personalrecord/prs", "personalRecords"),
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
                logger.debug("Non-JSON response for graphql-gateway on %s, skipping", url)

    return handler


def _is_page_crashed(page: Page) -> bool:
    """Check if the page has crashed and is no longer usable."""
    try:
        page.evaluate("1")
        return False
    except Exception:
        return True


def _recover_page(page: Page, context: BrowserContext) -> Page:
    """Close a crashed page and create a fresh one."""
    logger.info("Recovering from page crash — creating new page")
    try:
        page.close()
    except Exception:
        logger.debug("Could not close crashed page (already dead)")
    new_page = context.new_page()
    time.sleep(1)
    return new_page


def _navigate(
    page: Page,
    url: str,
    result: SyncResult,
    label: str,
    context: BrowserContext | None = None,
) -> Page:
    """Navigate to a page and track success/failure.

    Returns the page (may be a new page if recovery was needed).
    """
    if _is_page_crashed(page):
        if context is None:
            logger.error("Page crashed and no context for recovery — skipping %s", label)
            result.pages_failed.add(label)
            return page
        page = _recover_page(page, context)

    try:
        logger.info("Loading %s", label)
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    except Exception as e:
        logger.warning("Page load failed for %s: %s", label, e)
        result.pages_failed.add(label)
        if context and _is_page_crashed(page):
            page = _recover_page(page, context)
        return page

    # Wait for API responses — networkidle timeout is non-fatal because
    # Garmin's SPA keeps background requests running indefinitely.
    # The response handler captures data regardless.
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        logger.debug("networkidle timeout for %s (non-fatal, data captured via handler)", label)
    result.pages_loaded.add(label)

    return page


def sync_day(
    page: Page,
    date_str: str,
    include_activities: bool = True,
    pages: set[str] | None = None,
    context: BrowserContext | None = None,
) -> tuple[SyncResult, Page]:
    """Navigate daily pages and return all captured API responses.

    Args:
        page: The browser page to use.
        date_str: Date to sync (YYYY-MM-DD).
        include_activities: Whether to load the activities page (legacy flag).
        pages: Set of pages to load (e.g. {"daily", "sleep", "activities"}).
            When provided, this overrides include_activities.
            Defaults to ALL_PAGES if None.
        context: Browser context, used to recover from page crashes.

    Returns:
        A tuple of (SyncResult, page) — page may differ from input if recovery occurred.
    """
    if pages is None:
        pages = DEFAULT_PAGES.copy()
        if not include_activities:
            pages.discard("activities")

    result = SyncResult()
    handler = _make_response_handler(result.responses)
    page.on("response", handler)

    try:
        if "daily" in pages:
            page = _navigate(
                page,
                f"https://connect.garmin.com/app/daily-summary/{date_str}",
                result,
                f"daily summary ({date_str})",
                context,
            )

        if "sleep" in pages:
            page = _navigate(
                page,
                f"https://connect.garmin.com/app/sleep/{date_str}",
                result,
                f"sleep ({date_str})",
                context,
            )

        if "training-status" in pages:
            page = _navigate(
                page,
                f"https://connect.garmin.com/app/health-stats/training-status/{date_str}",
                result,
                f"training status ({date_str})",
                context,
            )

        if "body-composition" in pages:
            page = _navigate(
                page,
                "https://connect.garmin.com/app/body-composition",
                result,
                "body composition",
                context,
            )

        if "activities" in pages:
            page = _navigate(
                page,
                "https://connect.garmin.com/app/activities",
                result,
                "activities",
                context,
            )

        if "personal-records" in pages:
            page = _navigate(
                page,
                "https://connect.garmin.com/app/personal-records",
                result,
                "personal records",
                context,
            )

    finally:
        try:
            page.remove_listener("response", handler)
        except Exception:
            logger.debug("Could not remove response handler (page may have crashed)")

    logger.info(
        "Captured %d API responses (pages: %d ok, %d failed)",
        len(result.responses),
        len(result.pages_loaded),
        len(result.pages_failed),
    )
    return result, page
