import math
from typing import Any

from fastapi import HTTPException, status


def validate_coordinates(latitude: float, longitude: float) -> tuple[float, float]:
    lat = float(latitude)
    lon = float(longitude)
    if lat < -90 or lat > 90:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Latitude must be between -90 and 90")
    if lon < -180 or lon > 180:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Longitude must be between -180 and 180")
    return lat, lon


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    validate_coordinates(lat1, lon1)
    validate_coordinates(lat2, lon2)
    radius_km = 6371.0
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return radius_km * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def build_distance_matrix(points: list[dict[str, Any]]) -> list[list[int]]:
    matrix: list[list[int]] = []
    for origin in points:
        row: list[int] = []
        for destination in points:
            distance = haversine_distance_km(
                origin["latitude"],
                origin["longitude"],
                destination["latitude"],
                destination["longitude"],
            )
            row.append(int(round(distance * 1000)))
        matrix.append(row)
    return matrix


def calculate_route_distance_from_order(points: list[dict[str, Any]], order: list[int]) -> float:
    distance = 0.0
    for index in range(len(order) - 1):
        origin = points[order[index]]
        destination = points[order[index + 1]]
        distance += haversine_distance_km(
            origin["latitude"],
            origin["longitude"],
            destination["latitude"],
            destination["longitude"],
        )
    return round(distance, 3)
