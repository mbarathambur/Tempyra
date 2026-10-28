
from optimization.resource_optimizer import optimize_resources


def test_resource_limit():
    disasters = [
        {
            "disaster_id": "D001",
            "location": "Chennai",
            "severity": "High",
            "affected_people": 1200,
            "status": "Active"
        },
        {
            "disaster_id": "D002",
            "location": "Coimbatore",
            "severity": "Medium",
            "affected_people": 350,
            "status": "Active"
        }
    ]

    result = optimize_resources(disasters, 3)

    assert sum(
        item["teams_assigned"] for item in result
    ) <= 3

    assert all(
        item["teams_assigned"] >= 0 for item in result
    )
