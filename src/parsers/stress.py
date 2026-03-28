"""Parse stress data."""
from __future__ import annotations


def parse_stress(stress: dict) -> dict:
    """Extract stress metrics from dailyStress response."""
    return {
        "stressAvg": stress.get("overallStressLevel"),
    }
