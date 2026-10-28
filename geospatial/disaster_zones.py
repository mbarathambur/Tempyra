
from math import radians, sin, cos, asin, sqrt


def haversine_km(lat1, lon1, lat2, lon2):
    values = [lat1, lon1, lat2, lon2]

    if not all(-90 <= values[i] <= 90 for i in (0, 2)):
        raise ValueError("Latitude must be between -90 and 90.")

    if not all(-180 <= values[i] <= 180 for i in (1, 3)):
        raise ValueError("Longitude must be between -180 and 180.")

    lat1, lon1, lat2, lon2 = map(
        radians, [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    return 6371.0 * 2 * asin(sqrt(min(1.0, a)))


def find_nearby_disasters(
    disasters,
    latitude,
    longitude,
    radius_km=50,
):
    if not -90 <= latitude <= 90:
        raise ValueError("Invalid search latitude.")

    if not -180 <= longitude <= 180:
        raise ValueError("Invalid search longitude.")

    if radius_km < 0:
        raise ValueError("Radius cannot be negative.")

    nearby = []

    for disaster in disasters:
        if str(disaster.get("status", "")).strip().lower() != "active":
            continue

        distance = haversine_km(
            float(latitude),
            float(longitude),
            float(disaster["latitude"]),
            float(disaster["longitude"]),
        )

        if distance <= radius_km:
            item = dict(disaster)
            item["distance_km"] = round(distance, 2)
            nearby.append(item)

    return sorted(nearby, key=lambda item: item["distance_km"])
