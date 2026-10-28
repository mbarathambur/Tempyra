
import pandas as pd
import pytest

from optimization.resource_allocator import allocate_resources


def sample_disasters():
    return pd.DataFrame([
        {
            "disaster_id": "D1",
            "location": "Chennai",
            "severity": "High",
            "affected_people": 1200,
            "status": "Active",
        },
        {
            "disaster_id": "D2",
            "location": "Coimbatore",
            "severity": "Medium",
            "affected_people": 350,
            "status": "Active",
        },
        {
            "disaster_id": "D3",
            "location": "Madurai",
            "severity": "Low",
            "affected_people": 100,
            "status": "Monitoring",
        },
    ])


def test_allocation_never_exceeds_team_budget():
    result = allocate_resources(sample_disasters(), 3)

    assert result["teams_assigned"].sum() <= 3


def test_inactive_disasters_receive_no_teams():
    result = allocate_resources(sample_disasters(), 12)

    inactive = result[result["status"] != "Active"]

    assert (inactive["teams_assigned"] == 0).all()
    assert (inactive["allocation_status"] == "Not Active").all()


def test_high_severity_gets_priority():
    result = allocate_resources(sample_disasters(), 4)

    chennai = result[result["disaster_id"] == "D1"].iloc[0]

    assert chennai["teams_assigned"] == 4
    assert chennai["allocation_status"] == "Fully Allocated"


def test_zero_teams_leaves_active_disasters_unassigned():
    result = allocate_resources(sample_disasters(), 0)

    active = result[result["status"] == "Active"]

    assert (active["teams_assigned"] == 0).all()
    assert (active["allocation_status"] == "Unassigned").all()


@pytest.mark.parametrize("team_count", [-1, 1.5, True, float("inf"), "invalid"])
def test_rejects_invalid_team_budget(team_count):
    with pytest.raises(ValueError):
        allocate_resources(sample_disasters(), team_count)


def test_rejects_invalid_severity():
    disasters = sample_disasters()
    disasters.loc[0, "severity"] = "Critical"

    with pytest.raises(ValueError, match="Invalid severity"):
        allocate_resources(disasters, 12)


def test_rejects_negative_affected_population():
    disasters = sample_disasters()
    disasters.loc[0, "affected_people"] = -10

    with pytest.raises(ValueError, match="Affected people"):
        allocate_resources(disasters, 12)
