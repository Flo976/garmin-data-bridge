"""Tests for scraper crash-recovery, response-handler reattachment, and CF handling."""

import logging
from unittest.mock import MagicMock, call, patch

from src.scraper import SyncResult, _handle_cloudflare_challenge, _navigate, _recover_page, sync_day

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


# ---------------------------------------------------------------------------
# _handle_cloudflare_challenge
# ---------------------------------------------------------------------------


def _make_cf_page(cf_content: bool = False, resolves_after: int | None = None) -> MagicMock:
    """Return a mock Page for Cloudflare challenge tests.

    Args:
        cf_content: If True, first content() call returns CF challenge HTML.
        resolves_after: If set, content() returns CF content for this many
            additional calls (during polling) then switches to normal HTML.
    """
    page = MagicMock()
    normal_html = "<html><body>Garmin Connect</body></html>"
    cf_html = "<html><body>just a moment...</body></html>"

    if not cf_content:
        page.content.return_value = normal_html
        return page

    if resolves_after is None:
        # Always CF content (timeout scenario)
        page.content.return_value = cf_html
    else:
        # CF content for initial check + resolves_after polls, then normal
        side_effects = [cf_html] * (1 + resolves_after) + [normal_html]
        page.content.side_effect = side_effects

    # iframe/frame_locator setup: no checkbox found by default
    frame_locator = MagicMock()
    checkbox = MagicMock()
    checkbox.count.return_value = 0
    frame_locator.locator.return_value = checkbox
    page.frame_locator.return_value = frame_locator

    return page


def test_cf_no_challenge_returns_false():
    """Returns False immediately when no Cloudflare challenge is present."""
    page = _make_cf_page(cf_content=False)
    result = _handle_cloudflare_challenge(page)
    assert result is False
    page.frame_locator.assert_not_called()


def test_cf_resolves_quickly_returns_true():
    """Returns True when the challenge resolves within the polling window."""
    page = _make_cf_page(cf_content=True, resolves_after=2)

    with patch("src.scraper.random.uniform", return_value=1.0), patch("src.scraper.time.sleep"):
        result = _handle_cloudflare_challenge(page)

    assert result is True


def test_cf_times_out_returns_true():
    """Returns True even when challenge never resolves (timeout case)."""
    page = _make_cf_page(cf_content=True, resolves_after=None)

    with patch("src.scraper.random.uniform", return_value=1.0), patch("src.scraper.time.sleep"):
        result = _handle_cloudflare_challenge(page)

    assert result is True


def test_cf_jitter_sleep_called():
    """A sleep call with the jitter value is made before polling."""
    page = _make_cf_page(cf_content=True, resolves_after=0)

    with (
        patch("src.scraper.random.uniform", return_value=3.7) as mock_uniform,
        patch("src.scraper.time.sleep") as mock_sleep,
    ):
        _handle_cloudflare_challenge(page)

    mock_uniform.assert_called_once_with(1.0, 5.0)
    # First sleep call should use the jitter value
    assert mock_sleep.call_args_list[0] == call(3.7)


def test_cf_clicks_checkbox_when_found():
    """Clicks the Turnstile checkbox when the iframe and element are found."""
    page = _make_cf_page(cf_content=True, resolves_after=1)

    # Override the default "count=0" to simulate a found checkbox
    checkbox = MagicMock()
    checkbox.count.return_value = 1
    frame_locator = MagicMock()
    frame_locator.locator.return_value = checkbox
    page.frame_locator.return_value = frame_locator

    with patch("src.scraper.random.uniform", return_value=1.0), patch("src.scraper.time.sleep"):
        _handle_cloudflare_challenge(page)

    checkbox.first.click.assert_called_once_with(timeout=5_000)


def test_navigate_calls_cf_handler_after_goto():
    """_navigate must call _handle_cloudflare_challenge after a successful goto."""
    page = _make_page()
    result = SyncResult()

    with patch("src.scraper._handle_cloudflare_challenge") as mock_cf:
        _navigate(page, "https://example.com", result, "daily summary (2026-03-29)")

    mock_cf.assert_called_once_with(page)


# ---------------------------------------------------------------------------
# _navigate: crash detected during networkidle wait
# ---------------------------------------------------------------------------


def test_navigate_crash_during_networkidle_logs_warning_not_timeout(caplog):
    """When the page crashes during the networkidle wait the log should say
    'crashed' — not the misleading 'networkidle timeout' message."""
    page = MagicMock()
    # First evaluate: pre-navigation crash check → page alive.
    # Second evaluate: _is_page_crashed called inside the networkidle except
    #                  block → page has now crashed.
    page.evaluate.side_effect = [1, Exception("page crashed")]
    page.wait_for_load_state.side_effect = Exception("Target closed")
    result = SyncResult()

    with caplog.at_level(logging.WARNING, logger="src.scraper"):
        _navigate(page, "https://example.com", result, "body composition")

    assert any("crashed" in record.message for record in caplog.records)
    assert not any("networkidle timeout" in record.message for record in caplog.records)


def test_navigate_networkidle_timeout_no_crash_logs_debug_only(caplog):
    """A plain networkidle timeout (page still alive) must NOT emit a WARNING."""
    page = _make_page()  # page.evaluate always returns 1
    page.wait_for_load_state.side_effect = Exception("Timeout 5000ms exceeded")
    result = SyncResult()

    with caplog.at_level(logging.DEBUG, logger="src.scraper"):
        _navigate(page, "https://example.com", result, "sleep (2026-03-29)")

    warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert not warning_messages
    # debug message should be present
    assert any("networkidle timeout" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# sync_day: cascade crash recovery (issue #2)
# ---------------------------------------------------------------------------


def test_sync_day_cascade_crash_recovery():
    """After a crash during body-composition navigation, subsequent pages
    (activities, personal-records) must load successfully on the recovered page,
    and the response handler must be active to capture data from them.

    This reproduces the original cascade failure reported in issue #2.
    """
    # Original page: alive initially, but crashes when body-composition goto fires.
    original_page = MagicMock()
    original_page.evaluate.side_effect = [
        1,  # pre-crash check before body-composition goto
        Exception("page crashed"),  # post-goto crash detection
    ]
    original_page.goto.side_effect = Exception("Page.goto: Page crashed")

    # Recovered page: healthy for all subsequent navigations.
    recovered_page = MagicMock()
    recovered_page.evaluate.return_value = 1

    context = MagicMock()
    context.new_page.return_value = recovered_page

    with patch("src.scraper.time.sleep"), patch("src.scraper._handle_cloudflare_challenge"):
        result, final_page = sync_day(
            original_page,
            "2026-03-29",
            pages={"body-composition", "activities", "personal-records"},
            context=context,
        )

    # body-composition failed due to crash
    assert "body composition" in result.pages_failed

    # activities and personal-records should have succeeded on the recovered page
    assert "activities" in result.pages_loaded
    assert "personal records" in result.pages_loaded

    # The final page returned must be the recovered page, not the crashed one
    assert final_page is recovered_page

    # The handler must have been reattached: recovered_page.on("response", ...) called
    on_calls = [c for c in recovered_page.on.call_args_list if c.args[0] == "response"]
    assert on_calls, "Response handler was not reattached to the recovered page"
