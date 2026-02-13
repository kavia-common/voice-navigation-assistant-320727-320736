from __future__ import annotations

from typing import Any

import httpx

from src.api.config import Settings
from src.api.errors import AppError
from src.api.models import (
    DirectionsRequest,
    LatLng,
    PlaceCandidate,
    PlaceSearchRequest,
    RouteStep,
    RouteSummary,
)
from src.api.providers.maps.base import MapsProvider


class GoogleMapsProvider(MapsProvider):
    """Google Maps implementation backed by HTTP APIs."""

    def __init__(self, settings: Settings):
        self._settings = settings
        if not settings.google_maps_api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY must be provided for GoogleMapsProvider")

    async def search_places(self, request: PlaceSearchRequest) -> list[PlaceCandidate]:
        url = f"{self._settings.google_maps_base_url}/place/textsearch/json"
        params: dict[str, Any] = {
            "query": request.query,
            "key": self._settings.google_maps_api_key,
        }
        if request.near:
            params["location"] = f"{request.near.lat},{request.near.lng}"
            params["radius"] = int(request.radius_meters or 3000)

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
        data = resp.json()

        if resp.status_code != 200:
            raise AppError(
                code="maps_provider_error",
                message="Maps provider request failed.",
                http_status=502,
                details={"status_code": resp.status_code},
            )

        status_txt = data.get("status")
        if status_txt not in {"OK", "ZERO_RESULTS"}:
            raise AppError(
                code="maps_provider_error",
                message="Maps provider returned error status.",
                http_status=502,
                details={"provider_status": status_txt, "error_message": data.get("error_message")},
            )

        results = data.get("results", [])[: request.limit]
        candidates: list[PlaceCandidate] = []
        for r in results:
            loc = r.get("geometry", {}).get("location")
            location: LatLng | None = None
            if isinstance(loc, dict) and "lat" in loc and "lng" in loc:
                location = LatLng(lat=float(loc["lat"]), lng=float(loc["lng"]))

            candidates.append(
                PlaceCandidate(
                    place_id=r.get("place_id") or "",
                    name=r.get("name") or "Unknown",
                    address=r.get("formatted_address"),
                    location=location,
                    types=list(r.get("types") or []),
                )
            )
        return candidates

    async def get_directions(self, request: DirectionsRequest) -> RouteSummary:
        url = f"{self._settings.google_maps_base_url}/directions/json"

        if request.origin:
            origin = f"{request.origin.lat},{request.origin.lng}"
        elif request.origin_query:
            origin = request.origin_query
        else:
            raise AppError(
                code="missing_origin",
                message="Origin is required (origin or origin_query).",
                http_status=400,
            )

        if request.destination:
            destination = f"{request.destination.lat},{request.destination.lng}"
        elif request.destination_query:
            destination = request.destination_query
        else:
            raise AppError(
                code="missing_destination",
                message="Destination is required (destination or destination_query).",
                http_status=400,
            )

        params: dict[str, Any] = {
            "origin": origin,
            "destination": destination,
            "mode": request.mode,
            "key": self._settings.google_maps_api_key,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
        data = resp.json()

        if resp.status_code != 200:
            raise AppError(
                code="maps_provider_error",
                message="Maps provider request failed.",
                http_status=502,
                details={"status_code": resp.status_code},
            )

        status_txt = data.get("status")
        if status_txt != "OK":
            raise AppError(
                code="maps_provider_error",
                message="Maps provider returned error status.",
                http_status=502,
                details={"provider_status": status_txt, "error_message": data.get("error_message")},
            )

        routes = data.get("routes") or []
        if not routes:
            raise AppError(code="no_route", message="No route found.", http_status=404)

        route0 = routes[0]
        legs = route0.get("legs") or []
        if not legs:
            raise AppError(code="no_route", message="No route legs returned.", http_status=502)

        leg0 = legs[0]
        distance_m = int((leg0.get("distance") or {}).get("value") or 0)
        duration_s = int((leg0.get("duration") or {}).get("value") or 0)
        polyline = (route0.get("overview_polyline") or {}).get("points")

        steps: list[RouteStep] = []
        for s in leg0.get("steps") or []:
            # HTML instructions are returned by Google; strip tags minimally by removing angle brackets content.
            instr = str(s.get("html_instructions") or s.get("instructions") or "")
            # very small sanitizer: remove <...>
            cleaned = []
            in_tag = False
            for ch in instr:
                if ch == "<":
                    in_tag = True
                    continue
                if ch == ">":
                    in_tag = False
                    continue
                if not in_tag:
                    cleaned.append(ch)
            instr_text = "".join(cleaned).strip() or "Continue"
            steps.append(
                RouteStep(
                    instruction=instr_text,
                    distance_meters=int((s.get("distance") or {}).get("value") or 0) or None,
                    duration_seconds=int((s.get("duration") or {}).get("value") or 0) or None,
                )
            )

        return RouteSummary(
            distance_meters=max(0, distance_m),
            duration_seconds=max(0, duration_s),
            polyline=polyline,
            steps=steps,
        )
