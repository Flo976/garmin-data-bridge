"""Main entry point — orchestrates browser, auth, scraping, parsing, and upload."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

try:
    from patchright.sync_api import sync_playwright
except ImportError:
    from playwright.sync_api import sync_playwright

from src.browser import open_persistent_context
from src.auth import ensure_logged_in
from src.config import load_config
from src.parser import has_data, parse_daily_summary, parse_activities_list
from src.scraper import sync_day
from src.state import SyncState
from src.uploader import Uploader

logger = logging.getLogger(__name__)


def setup_logging(log_dir: str, verbose: bool = False) -> None:
    """Configure logging to stdout + file."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"{log_dir}/sync.log", encoding="utf-8"),
        ],
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="garmin-sync",
        description="Sync Garmin Connect data via browser interception",
    )
    p.add_argument(
        "--date", "-d",
        help="Sync a specific date (YYYY-MM-DD). Default: today",
    )
    p.add_argument(
        "--range", "-r",
        type=int,
        metavar="DAYS",
        help="Sync the last N days (backfill)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print data without uploading",
    )
    p.add_argument(
        "--login-only",
        action="store_true",
        help="Log in and save session, then exit",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return p.parse_args()


def _build_date_list(args: argparse.Namespace) -> list[str]:
    """Build list of dates to sync from CLI args."""
    if args.range:
        today = date.today()
        return [(today - timedelta(days=i)).isoformat() for i in range(args.range)]
    if args.date:
        return [args.date]
    return [date.today().isoformat()]


def _sync_one_day(
    page,
    date_str: str,
    uploader: Uploader | None,
    state: SyncState,
    dry_run: bool,
) -> dict:
    """Sync a single day. Returns the parsed daily summary."""
    responses = sync_day(page, date_str)

    daily = parse_daily_summary(responses, date_str)
    activities = parse_activities_list(responses)

    if dry_run:
        logger.info("--- DRY RUN: %s ---", date_str)
        print(json.dumps(daily, indent=2, default=str))
        if activities:
            print(json.dumps(activities, indent=2, default=str))
        return daily

    if has_data(daily) and uploader:
        uploader.upload_daily_summary(daily)
        logger.info(
            "[%s] Daily: steps=%s bb=%s hrv=%s sleep=%s",
            date_str,
            daily.get("steps"),
            daily.get("bodyBattery"),
            daily.get("hrvGarmin"),
            daily.get("sleepScore"),
        )
    else:
        logger.info("[%s] No daily data", date_str)

    if uploader:
        for act in activities:
            uploader.upload_activity(act)
    if activities:
        logger.info(
            "[%s] %d activite(s): %s",
            date_str,
            len(activities),
            ", ".join(f"{a.get('name', '?')} ({a['type']})" for a in activities),
        )

    state.mark_synced(date_str)
    return daily


def main() -> None:
    args = parse_args()
    cfg = load_config()
    setup_logging(cfg.log_dir, verbose=args.verbose)

    dates = _build_date_list(args)
    mode = "login-only" if args.login_only else (
        f"dry-run ({len(dates)} day(s))" if args.dry_run else f"{len(dates)} day(s)"
    )
    logger.info("=== Garmin Sync starting [%s] ===", mode)

    state = SyncState(cfg.log_dir)

    with sync_playwright() as pw:
        context = open_persistent_context(pw, cfg.browser_data_dir)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            ensure_logged_in(page, cfg.garmin_email, cfg.garmin_password)

            if args.login_only:
                logger.info("Login successful — session saved. Exiting.")
                context.close()
                return

            uploader = None if args.dry_run else Uploader(cfg.webhook_url, cfg.webhook_api_key)

            for date_str in dates:
                try:
                    _sync_one_day(page, date_str, uploader, state, args.dry_run)
                except Exception as e:
                    logger.error("[%s] Sync failed: %s", date_str, e)
                    # Continue with next day on per-day errors
                    continue

        except Exception as e:
            logger.error("Sync failed: %s", e, exc_info=True)
            sys.exit(1)
        finally:
            context.close()

    logger.info("=== Sync complete ===")


if __name__ == "__main__":
    main()
