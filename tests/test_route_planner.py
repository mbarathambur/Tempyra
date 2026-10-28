
import pytest
from geospatial.route_planner import plan_road_route


def test_same_start_and_end():
    result = plan_road_route(13.08, 80.27, 13.08, 80.27)

    assert result["status"] == "success"
    assert result["distance_km"] == 0.0


def test_invalid_coordinates():
    with pytest.raises(ValueError):
        plan_road_route(100, 80, 13, 80)


def test_rejects_excessive_distance():
    with pytest.raises(ValueError):
        plan_road_route(
            13.08, 80.27, 11.01, 76.95,
            max_straight_distance_km=50,
        )
