import json
from pathlib import Path
from src.parser import (
    parse_daily_summary,
    parse_activity,
    has_data,
    parse_activities_list,
    _extract_training_readiness,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict | list:
    return json.loads((FIXTURES / name).read_text())


def test_parse_daily_summary_full():
    responses = {
        "usersummary/daily": load_fixture("daily_summary_response.json"),
        "dailySleepData": load_fixture("sleep_response.json"),
        "dailyStress": load_fixture("stress_response.json"),
        "bodybattery": load_fixture("body_battery_response.json"),
        "hrv": load_fixture("hrv_response.json"),
    }

    result = parse_daily_summary(responses, "2026-03-28")

    assert result["date"] == "2026-03-28"
    assert result["steps"] == 8432
    assert result["calories"] == 2150
    assert result["restingHr"] == 52
    assert result["stressAvg"] == 32
    assert result["bodyBattery"] == 85
    assert result["hrvGarmin"] == 42.0
    assert result["sleepScore"] == 81
    assert result["sleepTotalMin"] == 450
    assert result["sleepDeepMin"] == 90
    assert result["sleepRemMin"] == 90
    assert result["sleepLightMin"] == 240
    assert result["sleepAwakeMin"] == 30


def test_parse_daily_summary_missing_sleep():
    responses = {
        "usersummary/daily": load_fixture("daily_summary_response.json"),
        "dailyStress": load_fixture("stress_response.json"),
        "bodybattery": load_fixture("body_battery_response.json"),
        "hrv": load_fixture("hrv_response.json"),
    }

    result = parse_daily_summary(responses, "2026-03-28")

    assert result["date"] == "2026-03-28"
    assert result["steps"] == 8432
    assert result["sleepScore"] is None
    assert result["sleepTotalMin"] is None


def test_parse_daily_summary_empty_responses():
    result = parse_daily_summary({}, "2026-03-28")

    assert result["date"] == "2026-03-28"
    assert result["steps"] is None
    assert result["sleepScore"] is None
    assert not has_data(result)


def test_parse_activity():
    activities = load_fixture("activities_response.json")
    result = parse_activity(activities[0])

    assert result["garminActivityId"] == "17234567890"
    assert result["date"] == "2026-03-28 07:30:00"
    assert result["type"] == "trail_running"
    assert result["name"] == "Trail Morning"
    assert result["durationS"] == 3845
    assert result["distanceM"] == 8234.5
    assert result["hrAvg"] == 148
    assert result["hrMax"] == 172
    assert result["calories"] == 680
    assert result["trainingEffectAerobic"] == 3.8
    assert result["trainingEffectAnaerobic"] == 1.2
    assert result["vo2maxUpdate"] == 52.0


def test_parse_activity_minimal():
    act = {
        "activityId": 999,
        "startTimeLocal": "2026-03-28 12:00:00",
        "activityType": {"typeKey": "other"},
        "duration": 600.0,
    }
    result = parse_activity(act)

    assert result["garminActivityId"] == "999"
    assert result["type"] == "other"
    assert result["durationS"] == 600
    assert result["distanceM"] is None
    assert result["hrAvg"] is None


def test_has_data_with_data():
    assert has_data({"date": "2026-03-28", "steps": 100})


def test_has_data_empty():
    assert not has_data({"date": "2026-03-28"})


def test_parse_activities_list():
    responses = {"activities": load_fixture("activities_response.json")}
    result = parse_activities_list(responses)
    assert len(result) == 2
    assert result[0]["garminActivityId"] == "17234567890"
    assert result[1]["garminActivityId"] == "17234567891"


def test_parse_activities_list_filtered_by_date():
    responses = {"activities": load_fixture("activities_response.json")}
    # Both fixture activities are on 2026-03-28
    result = parse_activities_list(responses, date_str="2026-03-28")
    assert len(result) == 2


def test_parse_activities_list_filtered_no_match():
    responses = {"activities": load_fixture("activities_response.json")}
    result = parse_activities_list(responses, date_str="2020-01-01")
    assert len(result) == 0


# --- Training Readiness ---

def test_training_readiness_dict_with_score():
    assert _extract_training_readiness({"score": 62}) == 62


def test_training_readiness_list_of_entries():
    assert _extract_training_readiness([{"score": 75, "date": "2026-03-28"}]) == 75


def test_training_readiness_nested_entries():
    assert _extract_training_readiness({"entries": [{"score": 58}]}) == 58


def test_training_readiness_none():
    assert _extract_training_readiness(None) is None
    assert _extract_training_readiness({}) is None
    assert _extract_training_readiness([]) is None


def test_parse_daily_summary_with_readiness_and_maxmet():
    responses = {
        "usersummary/daily": load_fixture("daily_summary_response.json"),
        "trainingReadiness": load_fixture("training_readiness_response.json"),
        "maxmet": load_fixture("maxmet_response.json"),
    }

    result = parse_daily_summary(responses, "2026-03-28")

    assert result["trainingReadiness"] == 62
    assert result["vo2max"] == 52.0
