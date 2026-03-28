"""Handle Garmin SSO authentication."""

from __future__ import annotations

import logging
import time
from pathlib import Path

try:
    from patchright.sync_api import Page
except ImportError:
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)

_GARMIN_HOME = "https://connect.garmin.com/modern/"
_SSO_MARKER = "sso.garmin.com"
_APP_MARKER = "connect.garmin.com/app/"
_LOGIN_TIMEOUT_MS = 30_000
_NAV_TIMEOUT_MS = 60_000
_CF_WAIT_MAX_S = 30
_MAX_LOGIN_RETRIES = 2
_DEBUG_DIR = Path.home() / ".garmin-sync" / "debug"


def _save_debug(page: Page, label: str) -> None:
    """Save a screenshot for debugging."""
    _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    path = _DEBUG_DIR / f"{label}.png"
    try:
        page.screenshot(path=str(path))
        logger.info("Debug screenshot: %s", path)
    except Exception:
        logger.debug("Debug screenshot failed for %s", label)


def _wait_for_cloudflare(page: Page) -> None:
    """Wait for Cloudflare challenge to resolve (JS challenge auto-solves)."""
    content = page.content().lower()
    if "just a moment" in content or "checking your browser" in content:
        logger.info("Cloudflare challenge detected — waiting for auto-resolve...")
        for i in range(_CF_WAIT_MAX_S):
            time.sleep(1)
            content = page.content().lower()
            if "just a moment" not in content and "checking your browser" not in content:
                logger.info("Cloudflare challenge resolved after %ds", i + 1)
                return
        logger.warning("Cloudflare challenge did not resolve after %ds", _CF_WAIT_MAX_S)


def ensure_logged_in(page: Page, email: str, password: str) -> None:
    """Navigate to Garmin Connect and log in if needed."""
    logger.info("Navigating to Garmin Connect...")
    page.goto(_GARMIN_HOME, timeout=_NAV_TIMEOUT_MS, wait_until="domcontentloaded")

    # Wait for Cloudflare if present
    _wait_for_cloudflare(page)
    page.wait_for_timeout(3000)

    url = page.url
    logger.info("Current URL: %s", url)

    if _APP_MARKER in url:
        logger.info("Session still valid — already logged in")
        return

    if _SSO_MARKER in url:
        logger.info("SSO login page detected — logging in")
        _do_login(page, email, password)
        return

    logger.warning("Unknown page state: %s", url)
    _save_debug(page, "unknown-state")
    _do_login(page, email, password)


def _do_login(page: Page, email: str, password: str, attempt: int = 1) -> None:
    """Fill SSO login form and submit."""
    try:
        # Wait for the login form — Garmin uses different field names
        logger.info("Waiting for login form (attempt %d/%d)...", attempt, _MAX_LOGIN_RETRIES)

        page.wait_for_selector(
            'input[name="username"], input[name="email"], input#email',
            timeout=_LOGIN_TIMEOUT_MS,
        )

        page.fill('input[name="username"], input[name="email"], input#email', email)
        page.fill('input[name="password"], input[type="password"], input#password', password)
        logger.info("Credentials filled, waiting for submit button to enable...")

        # Garmin has an internal Turnstile that keeps submit disabled until resolved
        submit = page.locator('button[type="submit"]')
        submit.wait_for(state="attached", timeout=_LOGIN_TIMEOUT_MS)

        # Wait for button to become enabled (Turnstile resolution)
        for i in range(60):
            if submit.is_enabled():
                break
            page.wait_for_timeout(1000)
            if i % 10 == 9:
                logger.info("Still waiting for submit button to enable (%ds)...", i + 1)
        else:
            _save_debug(page, f"submit-disabled-timeout-{attempt}")
            raise RuntimeError("Submit button stayed disabled for 60s")

        logger.info("Submit button enabled, clicking...")
        submit.click()

        page.wait_for_url(f"**/{_APP_MARKER}**", timeout=_LOGIN_TIMEOUT_MS)
        logger.info("Login successful — redirected to app")

    except Exception as e:
        _save_debug(page, f"login-fail-attempt-{attempt}")
        content = page.content()

        if attempt < _MAX_LOGIN_RETRIES and ("UNEXPECTED" in content.upper() or "just a moment" in content.lower()):
            label = "error banner" if "UNEXPECTED" in content.upper() else "Cloudflare"
            logger.warning("%s detected — retrying in 30s (attempt %d)", label, attempt)
            time.sleep(30)
            page.reload()
            _wait_for_cloudflare(page)
            page.wait_for_timeout(3000)
            _do_login(page, email, password, attempt + 1)
        else:
            logger.error("Login failed on attempt %d. Page title: %s", attempt, page.title())
            raise RuntimeError(f"Login failed: {e}") from e
