
from agents.response_workflow import run_response_workflow


def make_disaster(
    disaster_id,
    location,
    latitude,
    longitude,
    status="Active",
    severity="High",
):
    return {
        "disaster_id": disaster_id,
        "location": location,
        "disaster_type": "Flood",
        "severity": severity,
        "affected_people": 100,
        "latitude": latitude,
        "longitude": longitude,
        "status": status,
    }


def test_workflow_detects_nearby_active_disasters():
    disasters = [
        make_disaster("D1", "Location A", 13.0827, 80.2707),
        make_disaster("D2", "Location B", 13.1000, 80.2800),
    ]

    result = run_response_workflow(disasters, available_teams=8)

    first = next(
        item for item in result["geo_summary"]
        if item["disaster_id"] == "D1"
    )

    assert first["nearby_disaster_count"] == 1
    assert first["nearby_disasters"][0]["disaster_id"] == "D2"
    assert first["nearby_disasters"][0]["distance_km"] > 0


def test_workflow_excludes_inactive_incidents_from_nearby_results():
    disasters = [
        make_disaster("D1", "Location A", 13.0827, 80.2707),
        make_disaster(
            "D2",
            "Location B",
            13.0830,
            80.2710,
            status="Monitoring",
        ),
    ]

    result = run_response_workflow(disasters, available_teams=8)

    first = next(
        item for item in result["geo_summary"]
        if item["disaster_id"] == "D1"
    )

    assert first["nearby_disaster_count"] == 0
    assert first["nearby_disasters"] == []
