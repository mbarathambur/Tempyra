
import pytest

from agents.response_workflow import run_response_workflow


@pytest.fixture
def sample_disasters():
    return [
        {
            "disaster_id": "D001",
            "location": "Chennai",
            "disaster_type": "Flood",
            "severity": "High",
            "affected_people": 1200,
            "latitude": 13.0827,
            "longitude": 80.2707,
            "status": "Active",
        },
        {
            "disaster_id": "D002",
            "location": "Coimbatore",
            "disaster_type": "Storm",
            "severity": "Medium",
            "affected_people": 350,
            "latitude": 11.0168,
            "longitude": 76.9558,
            "status": "Active",
        },
    ]


def test_workflow_processes_disasters(sample_disasters):
    result = run_response_workflow(sample_disasters, 12)

    assert len(result["analysis"]) == 2
    assert len(result["geo_summary"]) == 2
    assert len(result["allocations"]) == 2
    assert result["response_plan"]


def test_high_severity_is_prioritized(sample_disasters):
    result = run_response_workflow(sample_disasters, 12)

    assert result["analysis"][0]["severity"] == "High"


def test_team_limit_is_respected(sample_disasters):
    available_teams = 3
    result = run_response_workflow(sample_disasters, available_teams)

    total_assigned = sum(
        int(item["teams_assigned"])
        for item in result["allocations"]
    )

    assert total_assigned <= available_teams


def test_invalid_coordinates_are_rejected(sample_disasters):
    sample_disasters[0]["latitude"] = 120

    with pytest.raises(ValueError):
        run_response_workflow(sample_disasters, 5)


def test_invalid_severity_is_rejected(sample_disasters):
    sample_disasters[0]["severity"] = "Extreme"

    with pytest.raises(ValueError):
        run_response_workflow(sample_disasters, 5)


def test_negative_team_count_is_rejected(sample_disasters):
    with pytest.raises(ValueError):
        run_response_workflow(sample_disasters, -1)


def test_empty_disaster_list(sample_disasters):
    result = run_response_workflow([], 5)

    assert result["analysis"] == []
    assert result["geo_summary"] == []
    assert result["allocations"] == []
    assert result["response_plan"]


def test_zero_teams_are_supported(sample_disasters):
    result = run_response_workflow(sample_disasters, 0)

    total_assigned = sum(
        int(item["teams_assigned"])
        for item in result["allocations"]
    )

    assert total_assigned == 0
