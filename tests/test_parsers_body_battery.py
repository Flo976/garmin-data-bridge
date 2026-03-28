import json
from pathlib import Path

from src.parsers.body_battery import parse_body_battery, parse_body_battery_events

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


def test_parse_body_battery():
    result = parse_body_battery(load("body_battery_response.json"))
    assert result["bodyBattery"] == 85
    assert result["bodyBatteryMin"] == 38


def test_parse_body_battery_empty():
    result = parse_body_battery([])
    assert result["bodyBattery"] is None


def test_parse_body_battery_events():
    result = parse_body_battery_events(load("body_battery_events_response.json"))
    assert len(result) == 2
    assert result[0]["eventType"] == "SLEEP"
    assert result[0]["bodyBatteryImpact"] == 45
    assert result[1]["eventType"] == "ACTIVITY"
    assert result[1]["activityName"] == "Trail Morning"


def test_parse_body_battery_events_none():
    assert parse_body_battery_events(None) == []
