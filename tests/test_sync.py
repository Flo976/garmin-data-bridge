import argparse
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.scraper import ALL_PAGES, DEFAULT_PAGES
from src.sync import _build_date_list, _parse_idle_timeout, _parse_pages, _sync_one_day, _validate_date


def _args(**kwargs):
    defaults = {"date": None, "range": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_build_date_list_default():
    result = _build_date_list(_args())
    assert result == [date.today().isoformat()]


def test_build_date_list_specific_date():
    result = _build_date_list(_args(date="2026-03-25"))
    assert result == ["2026-03-25"]


def test_build_date_list_range():
    result = _build_date_list(_args(range=3))
    today = date.today()
    expected = [(today - timedelta(days=i)).isoformat() for i in range(3)]
    assert result == expected


def test_build_date_list_range_overrides_date():
    result = _build_date_list(_args(date="2026-01-01", range=2))
    # --range takes precedence
    assert len(result) == 2
    assert result[0] == date.today().isoformat()


def test_validate_date_valid():
    assert _validate_date("2026-03-28") == "2026-03-28"


def test_validate_date_invalid():
    with pytest.raises(argparse.ArgumentTypeError, match="Invalid date"):
        _validate_date("yesterday")


def test_validate_date_bad_format():
    with pytest.raises(argparse.ArgumentTypeError, match="Invalid date"):
        _validate_date("28-03-2026")


# --- _parse_pages tests ---


def test_parse_pages_default():
    assert _parse_pages(None) == DEFAULT_PAGES


def test_parse_pages_single():
    assert _parse_pages("daily") == {"daily"}


def test_parse_pages_multiple():
    assert _parse_pages("daily,sleep") == {"daily", "sleep"}


def test_parse_pages_all():
    assert _parse_pages(",".join(sorted(ALL_PAGES))) == ALL_PAGES


def test_parse_pages_with_spaces():
    assert _parse_pages("daily , sleep") == {"daily", "sleep"}


def test_parse_pages_invalid():
    with pytest.raises(argparse.ArgumentTypeError, match="Unknown page"):
        _parse_pages("daily,banana")


def test_parse_pages_empty_string():
    with pytest.raises(argparse.ArgumentTypeError, match="at least one page"):
        _parse_pages("")


def test_parse_pages_env_var(monkeypatch):
    monkeypatch.setenv("SYNC_PAGES", "daily")
    assert _parse_pages(None) == {"daily"}


def test_parse_pages_cli_overrides_env(monkeypatch):
    monkeypatch.setenv("SYNC_PAGES", "daily")
    assert _parse_pages("sleep,activities") == {"sleep", "activities"}


# --- _parse_idle_timeout tests ---


def test_parse_idle_timeout_default(monkeypatch):
    monkeypatch.delenv("NETWORK_IDLE_TIMEOUT_MS", raising=False)
    assert _parse_idle_timeout() == 5_000


def test_parse_idle_timeout_from_env(monkeypatch):
    monkeypatch.setenv("NETWORK_IDLE_TIMEOUT_MS", "10000")
    assert _parse_idle_timeout() == 10_000


def test_parse_idle_timeout_zero_allowed(monkeypatch):
    monkeypatch.setenv("NETWORK_IDLE_TIMEOUT_MS", "0")
    assert _parse_idle_timeout() == 0


def test_parse_idle_timeout_invalid_string(monkeypatch):
    monkeypatch.setenv("NETWORK_IDLE_TIMEOUT_MS", "fast")
    with pytest.raises(argparse.ArgumentTypeError, match="non-negative integer"):
        _parse_idle_timeout()


def test_parse_idle_timeout_negative(monkeypatch):
    monkeypatch.setenv("NETWORK_IDLE_TIMEOUT_MS", "-1")
    with pytest.raises(argparse.ArgumentTypeError, match="non-negative integer"):
        _parse_idle_timeout()


# --- _sync_one_day upload-gating tests ---


def _make_sync_one_day_mocks(responses=None):
    """Return a (mock_page, mock_uploader, mock_result) tuple for _sync_one_day tests."""
    mock_result = MagicMock()
    mock_result.responses = responses or {}
    mock_result.is_complete = True
    mock_result.pages_failed = set()
    mock_result.pages_loaded = {"daily"}
    mock_page = MagicMock()
    mock_uploader = MagicMock()
    return mock_page, mock_uploader, mock_result


def test_sync_one_day_skips_personal_records_upload_when_not_in_pages():
    """Personal records should not be uploaded when 'personal-records' not in pages."""
    mock_page, mock_uploader, mock_result = _make_sync_one_day_mocks()
    fake_records = [{"type": "pr_fastest_5k", "value": 1380.0, "date": "2026-01-01", "activityId": 1}]

    with (
        patch("src.sync.sync_day", return_value=(mock_result, mock_page)),
        patch("src.sync.parse_daily_summary", return_value={"steps": 5000, "date": "2026-03-29"}),
        patch("src.sync.has_data", return_value=True),
        patch("src.sync.parse_activities_list", return_value=[]),
        patch("src.sync.parse_body_comp", return_value=None),
        patch("src.sync.parse_bb_events", return_value=None),
        patch("src.sync.parse_records", return_value=fake_records),
    ):
        ok, _ = _sync_one_day(
            page=mock_page,
            date_str="2026-03-29",
            uploader=mock_uploader,
            dry_run=False,
            is_today=True,
            pages={"daily"},
        )

    mock_uploader.upload_personal_records.assert_not_called()
    assert ok is True


def test_sync_one_day_uploads_personal_records_when_in_pages():
    """Personal records should be uploaded when 'personal-records' is in pages."""
    mock_page, mock_uploader, mock_result = _make_sync_one_day_mocks()
    fake_records = [{"type": "pr_fastest_5k", "value": 1380.0, "date": "2026-01-01", "activityId": 1}]

    with (
        patch("src.sync.sync_day", return_value=(mock_result, mock_page)),
        patch("src.sync.parse_daily_summary", return_value={"steps": 5000, "date": "2026-03-29"}),
        patch("src.sync.has_data", return_value=True),
        patch("src.sync.parse_activities_list", return_value=[]),
        patch("src.sync.parse_body_comp", return_value=None),
        patch("src.sync.parse_bb_events", return_value=None),
        patch("src.sync.parse_records", return_value=fake_records),
    ):
        ok, _ = _sync_one_day(
            page=mock_page,
            date_str="2026-03-29",
            uploader=mock_uploader,
            dry_run=False,
            is_today=True,
            pages={"daily", "personal-records"},
        )

    mock_uploader.upload_personal_records.assert_called_once()


def test_sync_one_day_skips_body_comp_upload_when_not_in_pages():
    """Body composition should not be uploaded when 'body-composition' not in pages."""
    mock_page, mock_uploader, mock_result = _make_sync_one_day_mocks()
    fake_body_comp = {"weightKg": 75.4, "bodyFatPct": 18.5}

    with (
        patch("src.sync.sync_day", return_value=(mock_result, mock_page)),
        patch("src.sync.parse_daily_summary", return_value={"steps": 5000, "date": "2026-03-29"}),
        patch("src.sync.has_data", return_value=True),
        patch("src.sync.parse_activities_list", return_value=[]),
        patch("src.sync.parse_body_comp", return_value=fake_body_comp),
        patch("src.sync.parse_bb_events", return_value=None),
        patch("src.sync.parse_records", return_value=[]),
    ):
        ok, _ = _sync_one_day(
            page=mock_page,
            date_str="2026-03-29",
            uploader=mock_uploader,
            dry_run=False,
            is_today=True,
            pages={"daily"},
        )

    mock_uploader.upload_body_comp.assert_not_called()
    assert ok is True


def test_sync_one_day_uploads_body_comp_when_in_pages():
    """Body composition should be uploaded when 'body-composition' is in pages."""
    mock_page, mock_uploader, mock_result = _make_sync_one_day_mocks()
    fake_body_comp = {"weightKg": 75.4, "bodyFatPct": 18.5}

    with (
        patch("src.sync.sync_day", return_value=(mock_result, mock_page)),
        patch("src.sync.parse_daily_summary", return_value={"steps": 5000, "date": "2026-03-29"}),
        patch("src.sync.has_data", return_value=True),
        patch("src.sync.parse_activities_list", return_value=[]),
        patch("src.sync.parse_body_comp", return_value=fake_body_comp),
        patch("src.sync.parse_bb_events", return_value=None),
        patch("src.sync.parse_records", return_value=[]),
    ):
        ok, _ = _sync_one_day(
            page=mock_page,
            date_str="2026-03-29",
            uploader=mock_uploader,
            dry_run=False,
            is_today=True,
            pages={"daily", "body-composition"},
        )

    mock_uploader.upload_body_comp.assert_called_once()


def test_sync_one_day_all_uploads_when_pages_is_none():
    """When pages=None (default), all upload types should fire if data is present."""
    mock_page, mock_uploader, mock_result = _make_sync_one_day_mocks()
    fake_records = [{"type": "pr_fastest_5k", "value": 1380.0, "date": "2026-01-01", "activityId": 1}]
    fake_body_comp = {"weightKg": 75.4, "bodyFatPct": 18.5}

    with (
        patch("src.sync.sync_day", return_value=(mock_result, mock_page)),
        patch("src.sync.parse_daily_summary", return_value={"steps": 5000, "date": "2026-03-29"}),
        patch("src.sync.has_data", return_value=True),
        patch("src.sync.parse_activities_list", return_value=[]),
        patch("src.sync.parse_body_comp", return_value=fake_body_comp),
        patch("src.sync.parse_bb_events", return_value=None),
        patch("src.sync.parse_records", return_value=fake_records),
    ):
        ok, _ = _sync_one_day(
            page=mock_page,
            date_str="2026-03-29",
            uploader=mock_uploader,
            dry_run=False,
            is_today=True,
            pages=None,
        )

    mock_uploader.upload_body_comp.assert_called_once()
    mock_uploader.upload_personal_records.assert_called_once()
