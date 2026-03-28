import json
from pathlib import Path
from src.parsers.vitals import parse_respiration, parse_spo2, parse_intensity_minutes, parse_floors

FIXTURES = Path(__file__).parent / "fixtures"

def load(name: str):
    return json.loads((FIXTURES / name).read_text())

def test_parse_respiration():
    result = parse_respiration(load("respiration_response.json"))
    assert result["respirationAvgWaking"] == 16.0
    assert result["respirationAvgSleep"] == 14.5
    assert result["respirationMin"] == 12.0
    assert result["respirationMax"] == 22.0

def test_parse_respiration_none():
    result = parse_respiration(None)
    assert result["respirationAvgWaking"] is None

def test_parse_spo2():
    result = parse_spo2(load("spo2_response.json"))
    assert result["spo2Avg"] == 96.0
    assert result["spo2Min"] == 92.0

def test_parse_spo2_none():
    result = parse_spo2(None)
    assert result["spo2Avg"] is None

def test_parse_intensity_minutes():
    result = parse_intensity_minutes(load("intensity_minutes_response.json"))
    assert result["intensityMinModerate"] == 15
    assert result["intensityMinVigorous"] == 10
    assert result["intensityMinWeeklyTotal"] == 135

def test_parse_intensity_minutes_none():
    result = parse_intensity_minutes(None)
    assert result["intensityMinModerate"] is None

def test_parse_floors():
    result = parse_floors(load("floors_response.json"))
    assert result["floorsClimbed"] == 12
    assert result["floorsDescended"] == 11

def test_parse_floors_empty():
    result = parse_floors([])
    assert result["floorsClimbed"] is None
