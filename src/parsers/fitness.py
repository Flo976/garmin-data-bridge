"""Parse fitness metrics (VO2max, training status/readiness, scores)."""
from __future__ import annotations


def _extract_first_score(raw: dict | list | None, key: str = "score") -> float | None:
    """Extract a score from various response shapes (dict, list, nested)."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        if key in raw:
            return raw[key]
        for container in ("entries", "days", "readiness"):
            items = raw.get(container, [])
            if isinstance(items, list) and items and isinstance(items[0], dict):
                return items[0].get(key)
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        return raw[0].get(key)
    return None


def parse_vo2max(maxmet_raw: list, summary: dict) -> float | None:
    """Extract VO2max from maxmet endpoint, fallback to daily summary."""
    if isinstance(maxmet_raw, list) and maxmet_raw:
        val = maxmet_raw[0].get("generic") or maxmet_raw[0].get("cycling")
        if val is not None:
            return val
    return summary.get("vo2Max")


def parse_training_readiness(raw: dict | list | None) -> float | None:
    """Extract training readiness score."""
    return _extract_first_score(raw, "score")


def parse_training_status(raw: dict | list | None) -> dict:
    """Extract training status from trainingstatus/aggregated response."""
    if raw is None:
        return {"trainingStatus": None, "trainingLoad7d": None}
    data = raw
    if isinstance(raw, list) and raw:
        data = raw[0]
    if not isinstance(data, dict):
        return {"trainingStatus": None, "trainingLoad7d": None}
    return {
        "trainingStatus": data.get("trainingStatus") or data.get("currentTrainingStatus"),
        "trainingLoad7d": data.get("trainingLoad7Day") or data.get("weeklyTrainingLoad"),
    }


def parse_endurance_score(raw: dict | list | None) -> float | None:
    """Extract endurance score."""
    return _extract_first_score(raw, "overallScore")


def parse_hill_score(raw: dict | list | None) -> float | None:
    """Extract hill score."""
    return _extract_first_score(raw, "overallScore")


def parse_fitness_age(raw: dict | None) -> int | None:
    """Extract fitness age from fitnessage response."""
    if not isinstance(raw, dict):
        return None
    return raw.get("fitnessAge") or raw.get("chronologicalFitnessAge")


def parse_race_predictions(raw: dict | list | None) -> dict:
    """Extract race time predictions."""
    if raw is None:
        return {}
    data = raw
    if isinstance(raw, list) and raw:
        data = raw[0]
    if not isinstance(data, dict):
        return {}
    return {
        "racePrediction5k": data.get("time5K"),
        "racePrediction10k": data.get("time10K"),
        "racePredictionHalf": data.get("timeHalfMarathon"),
        "racePredictionMarathon": data.get("timeMarathon"),
    }
