import json
from pathlib import Path

from src.parsers.records import parse_personal_records

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


def test_parse_personal_records():
    result = parse_personal_records(load("personal_records_response.json"))
    assert len(result) == 2
    assert result[0]["type"] == "pr_fastest_5k"
    assert result[0]["value"] == 1380.0
    assert result[1]["type"] == "pr_longest_run"


def test_parse_personal_records_none():
    assert parse_personal_records(None) == []
