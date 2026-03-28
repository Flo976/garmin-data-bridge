import json
from pathlib import Path

from src.parsers.fitness import (
    parse_endurance_score,
    parse_fitness_age,
    parse_hill_score,
    parse_race_predictions,
    parse_training_readiness,
    parse_training_status,
    parse_vo2max,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


def test_parse_training_status():
    result = parse_training_status(load("training_status_response.json"))
    assert result["trainingStatus"] == "PRODUCTIVE"
    assert result["trainingLoad7d"] == 524.5


def test_parse_training_status_none():
    result = parse_training_status(None)
    assert result["trainingStatus"] is None
    assert result["trainingLoad7d"] is None


def test_parse_endurance_score():
    assert parse_endurance_score(load("endurance_score_response.json")) == 72.0


def test_parse_endurance_score_none():
    assert parse_endurance_score(None) is None


def test_parse_hill_score():
    assert parse_hill_score(load("hill_score_response.json")) == 58.0


def test_parse_hill_score_none():
    assert parse_hill_score(None) is None


def test_parse_race_predictions():
    result = parse_race_predictions(load("race_predictions_response.json"))
    assert result["racePrediction5k"] == 1380.0
    assert result["racePrediction10k"] == 2940.0
    assert result["racePredictionHalf"] == 6600.0
    assert result["racePredictionMarathon"] == 14100.0


def test_parse_race_predictions_none():
    assert parse_race_predictions(None) == {}


def test_parse_fitness_age():
    assert parse_fitness_age(load("fitness_age_response.json")) == 28


def test_parse_fitness_age_none():
    assert parse_fitness_age(None) is None


def test_parse_training_readiness():
    assert parse_training_readiness({"score": 62}) == 62
    assert parse_training_readiness([{"score": 75}]) == 75
    assert parse_training_readiness(None) is None


def test_parse_vo2max_from_maxmet():
    assert parse_vo2max([{"generic": 52.0}], {}) == 52.0


def test_parse_vo2max_fallback():
    assert parse_vo2max([], {"vo2Max": 48.0}) == 48.0
