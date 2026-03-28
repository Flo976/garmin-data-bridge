"""Parse body composition / weight data."""
from __future__ import annotations


def parse_body_composition(raw: dict | None) -> dict:
    empty = {"weightKg": None, "bodyFatPct": None, "bmi": None, "muscleMassKg": None, "boneMassKg": None, "bodyWaterPct": None}
    if not isinstance(raw, dict):
        return empty
    entries = raw.get("dateWeightList", [])
    if not entries:
        return empty
    latest = entries[-1]
    weight_g = latest.get("weight")
    muscle_g = latest.get("muscleMass")
    bone_g = latest.get("boneMass")
    return {
        "weightKg": round(weight_g / 1000, 1) if weight_g else None,
        "bodyFatPct": latest.get("bodyFat"),
        "bmi": latest.get("bmi"),
        "muscleMassKg": round(muscle_g / 1000, 1) if muscle_g else None,
        "boneMassKg": round(bone_g / 1000, 1) if bone_g else None,
        "bodyWaterPct": latest.get("bodyWater"),
    }
