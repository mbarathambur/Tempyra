
import json
import math
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


def plan_road_route(
    start_lat,
    start_lon,
    end_lat,
    end_lon,
    max_straight_distance_km=100,
):
    """Find a driving route using OSRM without downloading an OSM road graph."""

    try:
        start_lat, start_lon, end_lat, end_lon = map(
            float, [start_lat, start_lon, end_lat, end_lon]
        )
        max_distance = float(max_straight_distance_km)
    except (TypeError, ValueError):
        raise ValueError("Coordinates must be valid numbers.")

    values = [start_lat, start_lon, end_lat, end_lon]

    if not all(math.isfinite(value) for value in values):
        raise ValueError("Coordinates must be finite numbers.")

    if not (-90 <= start_lat <= 90 and -90 <= end_lat <= 90):
        raise ValueError("Latitude must be between -90 and 90.")

    if not (-180 <= start_lon <= 180 and -180 <= end_lon <= 180):
        raise ValueError("Longitude must be between -180 and 180.")

    if not math.isfinite(max_distance) or max_distance <= 0:
        raise ValueError("Maximum distance must be positive.")

    lat1, lon1, lat2, lon2 = map(math.radians, values)

    a = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin((lon2 - lon1) / 2) ** 2
    )
    straight_km = 6371.0 * 2 * math.asin(
        math.sqrt(min(1.0, a))
    )

    if straight_km < 0.01:
        return {
            "status": "success",
            "distance_km": 0.0,
            "duration_minutes": 0.0,
            "route_coordinates": [[start_lat, start_lon]],
        }

    if straight_km > max_distance:
        raise ValueError(
            f"Locations are {straight_km:.1f} km apart; "
            f"limit is {max_distance:.1f} km."
        )

    coordinates = (
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
    )
    url = (
        f"{OSRM_URL}/{quote(coordinates, safe=',;')}"
        "?overview=full&geometries=geojson&steps=false"
    )

    request = Request(
        url,
        headers={"User-Agent": "Tempyra-Disaster-Response-Prototype/1.0"},
    )

    try:
        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("code") != "Ok" or not data.get("routes"):
            return {
                "status": "no_route",
                "message": data.get(
                    "message",
                    "No driving route was found between these locations.",
                ),
            }

        route = data["routes"][0]
        route_coordinates = [
            [float(lat), float(lon)]
            for lon, lat in route["geometry"]["coordinates"]
        ]

        return {
            "status": "success",
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_minutes": round(route["duration"] / 60, 1),
            "route_coordinates": route_coordinates,
        }

    except HTTPError as exc:
        return {
            "status": "error",
            "message": f"Routing service returned HTTP {exc.code}.",
        }

    except (URLError, TimeoutError, OSError) as exc:
        return {
            "status": "error",
            "message": (
                "The routing service could not be reached within "
                f"15 seconds. Check your internet connection. Details: {exc}"
            ),
        }

    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        return {
            "status": "error",
            "message": f"Unexpected response from the routing service: {exc}",
        }
