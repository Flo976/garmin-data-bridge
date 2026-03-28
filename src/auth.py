"""Handle Garmin SSO authentication."""

from __future__ import annotations

import logging
import time

from playwright.sync_api import Page

logger = logging.getLogger(__name__)

_GARMIN_HOME = "https://connect.garmin.com/modern/"
_SSO_MARKER = "sso.garmin.com"
_APP_MARKER = "connect.garmin.com/app/"
_LOGIN_TIMEOUT_MS = 30_000
_NAV_TIMEOUT_MS = 30_000


def ensure_logged_in(page: Page, email: str, password: str) -> None:
    """Navigate to Garmin Connect and log in if needed."""
    logger.info("Navigating to Garmin Connect...")
    page.goto(_GARMIN_HOME, timeout=_NAV_TIMEOUT_MS, wait_until="domcontentloaded")

    page.wait_for_timeout(3000)

    url = page.url
    if _APP_MARKER in url:
        logger.info("Session still valid — already logged in")
        return

    if _SSO_MARKER in url:
        logger.info("SSO login page detected — logging in")
        _do_login(page, email, password)
        return

    logger.warning("Unknown page state: %s — attempting login", url)
    _do_login(page, email, password)


def _do_login(page: Page, email: str, password: str) -> None:
    """Fill SSO login form and submit."""
    try:
        page.wait_for_selector('input[name="email"], input#email', timeout=_LOGIN_TIMEOUT_MS)

        page.fill('input[name="email"], input#email', email)
        page.fill('input[name="password"], input#password', password)

        page.click('button[type="submit"], #login-btn-signin')

        page.wait_for_url(f"**/{_APP_MARKER}**", timeout=_LOGIN_TIMEOUT_MS)
        logger.info("Login successful — redirected to app")

    except Exception as e:
        content = page.content()
        if "AN UNEXPECTED ERROR" in content.upper() or "UNEXPECTED" in content.upper():
            logger.warning("Garmin error banner detected — retrying in 30s")
            time.sleep(30)
            page.reload()
            _do_login(page, email, password)
        else:
            raise RuntimeError(f"Login failed: {e}") from e
