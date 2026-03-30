"""Tests for scraper crash-recovery and response-handler reattachment."""

from unittest.mock import MagicMock, patch

from src.scraper import SyncResult, _navigate, _recover_page

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_page(crashed: bool = False, goto_raises: Exception | None = None) -> MagicMock:
    """Return a mock Page that optionally reports as crashed or raises on goto."""
    page = MagicMock()
    if crashed:
        page.evaluate.side_effect = Exception("page crashed")
    else:
        page.evaluate.return_value = 1
    if goto_raises is not None:
        page.goto.side_effect = goto_raises
    return page


def _make_context() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# _recover_page
# ---------------------------------------------------------------------------


def test_recover_page_closes_old_and_returns_new():
    old_page = MagicMock()
    new_page = MagicMock()
    context = _make_context()
    context.new_page.return_value = new_page

    with patch("src.scraper.time.sleep"):
        result = _recover_page(old_page, context)

    old_page.close.assert_called_once()
    context.new_page.assert_called_once()
    assert result is new_page


def test_recover_page_tolerates_close_error():
    old_page = MagicMock()
    old_page.close.side_effect = Exception("already dead")
    new_page = MagicMock()
    context = _make_context()
    context.new_page.return_value = new_page

    with patch("src.scraper.time.sleep"):
        result = _recover_page(old_page, context)

    assert result is new_page


# ---------------------------------------------------------------------------
# _navigate: pre-navigation crash detection
# ---------------------------------------------------------------------------


def test_navigate_pre_crash_no_context_marks_failed():
    crashed_page = _make_page(crashed=True)
    result = SyncResult()

    returned_page = _navigate(crashed_page, "https://example.com", result, "test page")

    assert "test page" in result.pages_failed
    assert returned_page is crashed_page


def test_navigate_pre_crash_recovers_and_reattaches_handler():
    """After a pre-navigation crash, the handler must be attached to the new page."""
    crashed_page = _make_page(crashed=True)
    new_page = _make_page()
    context = _make_context()
    context.new_page.return_value = new_page

    handler = MagicMock()
    result = SyncResult()

    with patch("src.scraper.time.sleep"):
        returned_page = _navigate(
            crashed_page,
            "https://example.com",
            result,
            "test page",
            context,
            handler,
        )

    # The handler should have been attached to the new page
    new_page.on.assert_called_with("response", handler)
    assert returned_page is new_page
    assert "test page" in result.pages_loaded


def test_navigate_pre_crash_no_handler_does_not_call_on():
    """Recovery without a handler should not crash."""
    crashed_page = _make_page(crashed=True)
    new_page = _make_page()
    context = _make_context()
    context.new_page.return_value = new_page

    result = SyncResult()

    with patch("src.scraper.time.sleep"):
        returned_page = _navigate(crashed_page, "https://example.com", result, "test page", context)

    new_page.on.assert_not_called()
    assert returned_page is new_page


# ---------------------------------------------------------------------------
# _navigate: crash during page.goto
# ---------------------------------------------------------------------------


def test_navigate_crash_during_goto_reattaches_handler():
    """When page.goto raises Page crashed, recovery must reattach the handler.

    The page looks healthy on the pre-navigation check but is found crashed
    on the post-exception check (simulate by having evaluate succeed once then fail).
    """
    page = MagicMock()
    # First evaluate() → pre-check passes (page alive)
    # Second evaluate() → post-exception check detects crash
    page.evaluate.side_effect = [1, Exception("page crashed")]
    page.goto.side_effect = Exception("Page.goto: Page crashed")

    new_page = _make_page()
    context = _make_context()
    context.new_page.return_value = new_page

    handler = MagicMock()
    result = SyncResult()

    with patch("src.scraper.time.sleep"):
        returned_page = _navigate(
            page,
            "https://example.com",
            result,
            "body composition",
            context,
            handler,
        )

    new_page.on.assert_called_with("response", handler)
    assert "body composition" in result.pages_failed
    assert returned_page is new_page


def test_navigate_crash_during_goto_no_handler():
    """Crash during goto without a handler should not raise."""
    page = MagicMock()
    page.evaluate.side_effect = [1, Exception("page crashed")]
    page.goto.side_effect = Exception("Page.goto: Page crashed")

    new_page = _make_page()
    context = _make_context()
    context.new_page.return_value = new_page

    result = SyncResult()

    with patch("src.scraper.time.sleep"):
        returned_page = _navigate(page, "https://example.com", result, "activities", context)

    new_page.on.assert_not_called()
    assert "activities" in result.pages_failed
    assert returned_page is new_page


# ---------------------------------------------------------------------------
# _navigate: timeout (non-crash failure)
# ---------------------------------------------------------------------------


def test_navigate_timeout_marks_failed_no_recovery():
    """A timeout where the page did NOT crash should mark the page as failed
    but keep the same page object (no recovery needed)."""
    page = _make_page(goto_raises=Exception("Timeout 15000ms exceeded"))
    # Page still responds to evaluate → not crashed
    page.evaluate.return_value = 1

    result = SyncResult()

    returned_page = _navigate(page, "https://example.com", result, "sleep (2026-03-29)")

    assert "sleep (2026-03-29)" in result.pages_failed
    assert returned_page is page


# ---------------------------------------------------------------------------
# _navigate: successful navigation
# ---------------------------------------------------------------------------


def test_navigate_success_adds_to_loaded():
    page = _make_page()
    result = SyncResult()

    returned_page = _navigate(page, "https://example.com", result, "daily summary (2026-03-29)")

    assert "daily summary (2026-03-29)" in result.pages_loaded
    assert returned_page is page


# ---------------------------------------------------------------------------
# _navigate: idle_timeout_ms is forwarded to wait_for_load_state
# ---------------------------------------------------------------------------


def test_navigate_passes_idle_timeout_to_wait_for_load_state():
    """The idle_timeout_ms parameter must be forwarded to wait_for_load_state."""
    page = _make_page()
    result = SyncResult()

    _navigate(page, "https://example.com", result, "daily summary (2026-03-29)", idle_timeout_ms=3_000)

    page.wait_for_load_state.assert_called_once_with("networkidle", timeout=3_000)


def test_navigate_default_idle_timeout_is_5_seconds():
    """Default idle_timeout_ms should be 5000ms."""
    page = _make_page()
    result = SyncResult()

    _navigate(page, "https://example.com", result, "sleep (2026-03-29)")

    page.wait_for_load_state.assert_called_once_with("networkidle", timeout=5_000)
