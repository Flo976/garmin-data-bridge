"""Main entry point — orchestrates browser, auth, scraping, parsing, and upload."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

try:
    from patchright.sync_api import sync_playwright
except ImportError:
    from playwright.sync_api import sync_playwright

from src.auth import ensure_logged_in
from src.browser import open_persistent_context
from src.config import load_config
from src.parser import (
    has_data,
    parse_activities_list,
    parse_bb_events,
    parse_body_comp,
    parse_daily_summary,
    parse_records,
)
from src.scraper import ALL_PAGES, DEFAULT_PAGES, sync_day
from src.state import SyncState
from src.uploader import Uploader, UploadError

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
        "--date",
        "-d",
        help="Sync a specific date (YYYY-MM-DD). Default: today",
    )
    p.add_argument(
        "--range",
        "-r",
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
        "--force",
        action="store_true",
        help="Re-sync even if already synced",
    )
    p.add_argument(
        "--pages",
        type=str,
        metavar="PAGES",
        help=(
            f"Comma-separated list of pages to sync: {', '.join(sorted(ALL_PAGES))}. "
            f"Default: {','.join(sorted(DEFAULT_PAGES))}"
        ),
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return p.parse_args()


def _validate_date(date_str: str) -> str:
    """Validate and return a date string in YYYY-MM-DD format."""
    try:
        date.fromisoformat(date_str)
        return date_str
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date: '{date_str}'. Use YYYY-MM-DD format.")


def _build_date_list(args: argparse.Namespace) -> list[str]:
    """Build list of dates to sync from CLI args."""
    if args.range:
        today = date.today()
        return [(today - timedelta(days=i)).isoformat() for i in range(args.range)]
    if args.date:
        return [_validate_date(args.date)]
    return [date.today().isoformat()]


def _parse_pages(pages_arg: str | None) -> set[str]:
    """Parse --pages argument into a set of page names.

    Falls back to SYNC_PAGES env var if --pages is not provided.
    """
    if pages_arg is None:
        pages_arg = os.getenv("SYNC_PAGES")
    if pages_arg is None:
        return DEFAULT_PAGES.copy()
    requested = {p.strip().lower() for p in pages_arg.split(",") if p.strip()}
    invalid = requested - ALL_PAGES
    if invalid:
        raise argparse.ArgumentTypeError(
            f"Unknown page(s): {', '.join(sorted(invalid))}. Valid pages: {', '.join(sorted(ALL_PAGES))}"
        )
    if not requested:
        raise argparse.ArgumentTypeError("--pages requires at least one page")
    return requested


def _sync_one_day(
    page,
    date_str: str,
    uploader: Uploader | None,
    dry_run: bool,
    is_today: bool,
    pages: set[str] | None = None,
    context=None,
) -> tuple[bool, object]:
    """Sync a single day. Returns (success, page) — page may change after crash recovery."""
    # Filter activities/records to today only (avoids re-uploading on backfill)
    effective_pages = pages
    if effective_pages is not None and not is_today:
        effective_pages = effective_pages - {"activities", "personal-records"}

    result, page = sync_day(page, date_str, include_activities=is_today, pages=effective_pages, context=context)

    daily = parse_daily_summary(result.responses, date_str)
    include_act = is_today and (effective_pages is None or "activities" in effective_pages)
    activities = parse_activities_list(result.responses, date_str) if include_act else []

    if dry_run:
        logger.info("--- DRY RUN: %s ---", date_str)
        print(json.dumps(daily, indent=2, default=str))
        body_comp = parse_body_comp(result.responses)
        if body_comp:
            print(json.dumps({"body_composition": body_comp}, indent=2, default=str))
        bb_events = parse_bb_events(result.responses)
        if bb_events:
            print(json.dumps({"body_battery_events": bb_events}, indent=2, default=str))
        records = parse_records(result.responses)
        if records:
            print(json.dumps({"personal_records": records}, indent=2, default=str))
        if activities:
            print(json.dumps({"activities": activities}, indent=2, default=str))
        return True, page

    upload_ok = True

    if has_data(daily) and uploader:
        try:
            uploader.upload_daily_summary(daily)
            logger.info(
                "[%s] Daily: steps=%s bb=%s hrv=%s sleep=%s",
                date_str,
                daily.get("steps"),
                daily.get("bodyBattery"),
                daily.get("hrvGarmin"),
                daily.get("sleepScore"),
            )
        except UploadError as e:
            logger.error("[%s] Daily summary upload failed: %s", date_str, e)
            upload_ok = False
    else:
        logger.info("[%s] No daily data", date_str)

    if uploader:
        for act in activities:
            try:
                uploader.upload_activity(act)
            except UploadError as e:
                logger.error("[%s] Activity upload failed: %s", date_str, e)
                upload_ok = False
    if activities:
        logger.info(
            "[%s] %d activite(s): %s",
            date_str,
            len(activities),
            ", ".join(f"{a.get('name', '?')} ({a['type']})" for a in activities),
        )

    # Body composition
    body_comp = parse_body_comp(result.responses)
    if body_comp and uploader:
        try:
            uploader.upload_body_comp(body_comp)
            logger.info(
                "[%s] Body comp: weight=%s bf=%s%%",
                date_str,
                body_comp.get("weightKg"),
                body_comp.get("bodyFatPct"),
            )
        except UploadError as e:
            logger.error("[%s] Body comp upload failed: %s", date_str, e)
            upload_ok = False

    # Personal records (only for today)
    if is_today:
        records = parse_records(result.responses)
        if records and uploader:
            try:
                uploader.upload_personal_records(records)
                logger.info("[%s] %d personal record(s)", date_str, len(records))
            except UploadError as e:
                logger.error("[%s] Personal records upload failed: %s", date_str, e)
                upload_ok = False

    if not result.is_complete:
        logger.warning("[%s] Partial data (failed pages: %s)", date_str, result.pages_failed)
        upload_ok = False

    return upload_ok, page


def main() -> None:
    args = parse_args()
    cfg = load_config()
    setup_logging(cfg.log_dir, verbose=args.verbose)

    try:
        pages = _parse_pages(args.pages)
    except argparse.ArgumentTypeError as e:
        logger.error(str(e))
        sys.exit(1)

    dates = _build_date_list(args)
    today_str = date.today().isoformat()
    mode = (
        "login-only"
        if args.login_only
        else (f"dry-run ({len(dates)} day(s))" if args.dry_run else f"{len(dates)} day(s)")
    )
    pages_label = ",".join(sorted(pages))
    logger.info("=== Garmin Sync starting [%s, pages: %s] ===", mode, pages_label)

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
                if not args.force and not args.dry_run and state.is_synced(date_str):
                    logger.info("[%s] Already synced — skipping (use --force to re-sync)", date_str)
                    continue

                try:
                    is_today = date_str == today_str
                    ok, page = _sync_one_day(
                        page,
                        date_str,
                        uploader,
                        args.dry_run,
                        is_today,
                        pages=pages,
                        context=context,
                    )
                    if ok and not args.dry_run:
                        state.mark_synced(date_str)
                except Exception as e:
                    logger.error("[%s] Sync failed: %s", date_str, e)
                    continue

        except Exception as e:
            logger.error("Sync failed: %s", e, exc_info=True)
            sys.exit(1)
        finally:
            context.close()

    logger.info("=== Sync complete ===")


if __name__ == "__main__":
    main()
