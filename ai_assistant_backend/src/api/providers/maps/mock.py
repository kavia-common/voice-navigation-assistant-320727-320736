from __future__ import annotations

import math
from typing import Final

from src.api.models import (
    DirectionsRequest,
    PlaceCandidate,
    PlaceSearchRequest,
    RouteStep,
    RouteSummary,
)
from src.api.providers.maps.base import MapsProvider

_DEFAULT_CENTER: Final = (37.7749, -122.4194)  # SF


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """Approximate distance between two points in meters."""
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return int(2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


class MockMapsProvider(MapsProvider):
    """Safe fallback provider that returns deterministic mock results.

    This allows frontend development and basic end-to-end integration without API keys.
    """

    async def search_places(self, request: PlaceSearchRequest) -> list[PlaceCandidate]:
        center_lat = request.near.lat if request.near else _DEFAULT_CENTER[0]
        center_lng = request.near.lng if request.near else _DEFAULT_CENTER[1]

        # Deterministic pseudo-results based on query; no external calls.
        base_name = request.query.strip().title()
        candidates: list[PlaceCandidate] = []
        for i in range(request.limit):
            dlat = 0.002 * (i + 1)
            dlng = -0.002 * (i + 1)
            candidates.append(
                PlaceCandidate(
                    place_id=f"mock-{base_name.lower().replace(' ', '-')}-{i+1}",
                    name=f"{base_name} #{i+1}",
                    address="Mock Address",
                    location={"lat": center_lat + dlat, "lng": center_lng + dlng},
                    types=["mock", "point_of_interest"],
                )
            )
        return candidates

    async def get_directions(self, request: DirectionsRequest) -> RouteSummary:
        # For mock, require destination in some form
        origin_lat = request.origin.lat if request.origin else _DEFAULT_CENTER[0]
        origin_lng = request.origin.lng if request.origin else _DEFAULT_CENTER[1]
        dest_lat = request.destination.lat if request.destination else origin_lat + 0.01
        dest_lng = request.destination.lng if request.destination else origin_lng + 0.01

        distance = max(1, _haversine_m(origin_lat, origin_lng, dest_lat, dest_lng))
        # Simple speed assumptions
        speed_mps = {
            "walking": 1.4,
            "bicycling": 4.0,
            "transit": 8.0,
            "driving": 12.0,
        }.get(request.mode, 10.0)
        duration = max(1, int(distance / speed_mps))

        steps = [
            RouteStep(instruction="Head to your destination (mock).", distance_meters=distance, duration_seconds=duration)
        ]
        return RouteSummary(distance_meters=distance, duration_seconds=duration, polyline=None, steps=steps)
