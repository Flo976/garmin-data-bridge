"""Manage a persistent Chromium browser context via Playwright."""

from __future__ import annotations

import logging
from pathlib import Path

from playwright.sync_api import Playwright, BrowserContext

logger = logging.getLogger(__name__)

_SYSTEM_CHROMIUM = "/usr/bin/chromium-browser"

_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-translate",
    "--mute-audio",
    "--no-first-run",
]


def open_persistent_context(
    pw: Playwright,
    user_data_dir: str,
) -> BrowserContext:
    """Open a persistent Chromium context, reusing cookies from previous runs."""
    Path(user_data_dir).mkdir(parents=True, exist_ok=True)

    executable = _SYSTEM_CHROMIUM if Path(_SYSTEM_CHROMIUM).exists() else None

    kwargs = dict(
        user_data_dir=user_data_dir,
        headless=False,
        viewport={"width": 1280, "height": 900},
        args=_BROWSER_ARGS,
    )
    if executable:
        kwargs["executable_path"] = executable
        logger.info("Using system Chromium: %s", executable)
    else:
        kwargs["channel"] = "chromium"
        logger.info("Using Playwright-managed Chromium")

    context = pw.chromium.launch_persistent_context(**kwargs)
    logger.info("Browser context opened (data dir: %s)", user_data_dir)
    return context
