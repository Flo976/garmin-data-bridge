"""Manage a persistent Chromium browser context via Playwright."""

from __future__ import annotations

import logging
from pathlib import Path

try:
    from patchright.sync_api import Playwright, BrowserContext
except ImportError:
    from playwright.sync_api import Playwright, BrowserContext

logger = logging.getLogger(__name__)

_CHROME_CANDIDATES = [
    "/opt/google/chrome/chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
]

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


def _find_chrome() -> str | None:
    """Find a real Chrome/Chromium binary on the system."""
    for path in _CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    return None


def open_persistent_context(
    pw: Playwright,
    user_data_dir: str,
) -> BrowserContext:
    """Open a persistent Chrome context, reusing cookies from previous runs."""
    Path(user_data_dir).mkdir(parents=True, exist_ok=True)

    executable = _find_chrome()

    kwargs = dict(
        user_data_dir=user_data_dir,
        headless=False,
        viewport={"width": 1280, "height": 900},
        args=_BROWSER_ARGS,
    )
    if executable:
        kwargs["executable_path"] = executable
        logger.info("Using system Chrome: %s", executable)
    else:
        kwargs["channel"] = "chrome"
        logger.info("No system Chrome found, trying Playwright channel 'chrome'")

    context = pw.chromium.launch_persistent_context(**kwargs)
    logger.info("Browser context opened (data dir: %s)", user_data_dir)
    return context
