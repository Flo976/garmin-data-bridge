"""Main entry point — orchestrates browser, auth, scraping, parsing, and upload."""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

from src.browser import open_persistent_context
from src.auth import ensure_logged_in
from src.config import load_config
from src.parser import has_data, parse_daily_summary, parse_activities_list
from src.scraper import sync_day
from src.uploader import Uploader

logger = logging.getLogger(__name__)


def setup_logging(log_dir: str) -> None:
    """Configure logging to stdout + file."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"{log_dir}/sync.log", encoding="utf-8"),
        ],
    )


def main() -> None:
    cfg = load_config()
    setup_logging(cfg.log_dir)

    logger.info("=== Garmin Sync starting ===")

    with sync_playwright() as pw:
        context = open_persistent_context(pw, cfg.browser_data_dir)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            # 1. Auth
            ensure_logged_in(page, cfg.garmin_email, cfg.garmin_password)

            # 2. Scrape today's data
            today = date.today().isoformat()
            responses = sync_day(page, today)

            # 3. Parse
            daily = parse_daily_summary(responses, today)
            activities = parse_activities_list(responses)

            uploader = Uploader(cfg.webhook_url, cfg.webhook_api_key)

            # 4. Upload daily summary
            if has_data(daily):
                uploader.upload_daily_summary(daily)
                logger.info(
                    "Daily summary: steps=%s bb=%s hrv=%s sleep=%s",
                    daily.get("steps"),
                    daily.get("bodyBattery"),
                    daily.get("hrvGarmin"),
                    daily.get("sleepScore"),
                )
            else:
                logger.info("No daily data to upload")

            # 5. Upload activities
            for act in activities:
                uploader.upload_activity(act)
            if activities:
                logger.info(
                    "%d activite(s): %s",
                    len(activities),
                    ", ".join(f"{a['name']} ({a['type']})" for a in activities),
                )

        except Exception as e:
            logger.error("Sync failed: %s", e, exc_info=True)
            sys.exit(1)
        finally:
            context.close()

    logger.info("=== Sync complete ===")


if __name__ == "__main__":
    main()
