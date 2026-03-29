import argparse
from datetime import date, timedelta

import pytest

from src.scraper import ALL_PAGES, DEFAULT_PAGES
from src.sync import _build_date_list, _parse_pages, _validate_date


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
