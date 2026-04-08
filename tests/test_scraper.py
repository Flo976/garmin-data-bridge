"""Tests for scraper crash-recovery, response-handler reattachment, and CF handling."""

import json
from unittest.mock import MagicMock, call, patch

from src.scraper import (
    SyncResult,
    _extract_multipart_boundary,
    _handle_cloudflare_challenge,
    _make_response_handler,
    _navigate,
    _parse_multipart_graphql_body,
    _recover_page,
)

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
# _extract_multipart_boundary
# ---------------------------------------------------------------------------


def test_extract_boundary_unquoted():
    ct = "multipart/mixed; boundary=graphql"
    assert _extract_multipart_boundary(ct) == "graphql"


def test_extract_boundary_quoted():
    ct = 'multipart/mixed; boundary="-"'
    assert _extract_multipart_boundary(ct) == "-"


def test_extract_boundary_missing():
    assert _extract_multipart_boundary("application/json") is None


def test_extract_boundary_case_insensitive():
    ct = "multipart/mixed; Boundary=abc123"
    assert _extract_multipart_boundary(ct) == "abc123"


# ---------------------------------------------------------------------------
# _parse_multipart_graphql_body
# ---------------------------------------------------------------------------


def _make_multipart(boundary: str, parts: list[dict]) -> bytes:
    """Build a minimal multipart/mixed body from a list of JSON payloads."""
    lines = []
    sep = f"--{boundary}"
    for payload in parts:
        lines.append(sep)
        lines.append("Content-Type: application/json")
        lines.append("")
        lines.append(json.dumps(payload))
    lines.append(f"{sep}--")
    return "\r\n".join(lines).encode()


def test_parse_multipart_single_part():
    body = _make_multipart("graphql", [{"data": {"trainingStatus": {"status": "productive"}}}])
    result = _parse_multipart_graphql_body(body, "graphql")
    assert result == {"trainingStatus": {"status": "productive"}}


def test_parse_multipart_merges_incremental():
    parts = [
        {"data": {"trainingStatus": {"status": "productive"}}, "hasNext": True},
        {"incremental": [{"data": {"fitnessAge": 30}, "path": []}], "hasNext": False},
    ]
    body = _make_multipart("-", parts)
    result = _parse_multipart_graphql_body(body, "-")
    assert result["trainingStatus"] == {"status": "productive"}
    assert result["fitnessAge"] == 30


def test_parse_multipart_empty_body():
    result = _parse_multipart_graphql_body(b"", "graphql")
    assert result == {}


def test_parse_multipart_ignores_invalid_json_parts():
    boundary = "graphql"
    sep = f"--{boundary}"
    body = f"{sep}\r\nContent-Type: application/json\r\n\r\nnot-json\r\n{sep}--".encode()
    result = _parse_multipart_graphql_body(body, boundary)
    assert result == {}


# ---------------------------------------------------------------------------
# _make_response_handler — GraphQL branch
# ---------------------------------------------------------------------------


def _make_gql_response(content_type: str, body: bytes | None = None, json_data: dict | None = None) -> MagicMock:
    """Build a mock Playwright Response for graphql-gateway calls."""
    resp = MagicMock()
    resp.status = 200
    resp.url = "https://connect.garmin.com/gc-api/graphql-gateway/graphql"
    resp.headers = {"content-type": content_type}
    if body is not None:
        resp.body.return_value = body
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError("not JSON")
    return resp


def test_handler_captures_standard_json_graphql():
    captured: dict = {}
    handler = _make_response_handler(captured)
    resp = _make_gql_response(
        "application/json",
        json_data={"data": {"trainingStatus": {"status": "productive"}}},
    )
    handler(resp)
    assert "graphql/trainingStatus" in captured
    assert captured["graphql/trainingStatus"] == {"status": "productive"}


def test_handler_captures_multipart_graphql():
    parts = [
        {"data": {"trainingStatus": {"status": "productive"}}, "hasNext": True},
        {"incremental": [{"data": {"fitnessAge": 28}, "path": []}], "hasNext": False},
    ]
    body = _make_multipart("graphql", parts)
    captured: dict = {}
    handler = _make_response_handler(captured)
    resp = _make_gql_response("multipart/mixed; boundary=graphql", body=body)
    handler(resp)
    assert captured.get("graphql/trainingStatus") == {"status": "productive"}
    assert captured.get("graphql/fitnessAge") == 28


def test_handler_skips_graphql_when_no_boundary():
    captured: dict = {}
    handler = _make_response_handler(captured)
    resp = _make_gql_response("multipart/mixed")  # no boundary param
    resp.body.return_value = b""
    handler(resp)
    assert not any(k.startswith("graphql/") for k in captured)


def test_handler_skips_graphql_on_exception():
    captured: dict = {}
    handler = _make_response_handler(captured)
    resp = _make_gql_response("multipart/mixed; boundary=graphql")
    resp.body.side_effect = RuntimeError("network error")
    handler(resp)  # must not raise
    assert not any(k.startswith("graphql/") for k in captured)
