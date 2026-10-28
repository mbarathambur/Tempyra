
import pytest
from geospatial.disaster_zones import (
    haversine_km,
    find_nearby_disasters,
)


def test_same_location_distance():
    assert haversine_km(13.08, 80.27, 13.08, 80.27) == 0


def test_finds_nearby_active_disaster():
    disasters = [
        {
            "disaster_id": "D001",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "status": "Active",
        },
        {
            "disaster_id": "D002",
            "latitude": 11.0168,
            "longitude": 76.9558,
            "status": "Active",
        },
    ]

    result = find_nearby_disasters(
        disasters, 13.08, 80.27, radius_km=10
    )

    assert len(result) == 1
    assert result[0]["disaster_id"] == "D001"


def test_invalid_latitude_rejected():
    with pytest.raises(ValueError):
        haversine_km(100, 80, 13, 80)
