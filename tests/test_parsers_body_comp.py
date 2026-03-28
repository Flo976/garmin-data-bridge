import json
from pathlib import Path
from src.parsers.body_comp import parse_body_composition

FIXTURES = Path(__file__).parent / "fixtures"

def load(name: str):
    return json.loads((FIXTURES / name).read_text())

def test_parse_body_comp():
    result = parse_body_composition(load("body_comp_response.json"))
    assert result["weightKg"] == 75.4
    assert result["bodyFatPct"] == 18.5
    assert result["bmi"] == 23.8
    assert result["muscleMassKg"] == 34.2
    assert result["boneMassKg"] == 3.2
    assert result["bodyWaterPct"] == 55.2

def test_parse_body_comp_none():
    result = parse_body_composition(None)
    assert result["weightKg"] is None

def test_parse_body_comp_empty():
    result = parse_body_composition({"dateWeightList": []})
    assert result["weightKg"] is None
