import argparse
from datetime import date, timedelta

import pytest

from src.sync import _build_date_list, _validate_date


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
