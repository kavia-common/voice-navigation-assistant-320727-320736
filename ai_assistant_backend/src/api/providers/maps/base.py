from __future__ import annotations

from abc import ABC, abstractmethod

from src.api.models import DirectionsRequest, PlaceCandidate, PlaceSearchRequest, RouteSummary


class MapsProvider(ABC):
    """Abstract interface for map-related operations."""

    @abstractmethod
    async def search_places(self, request: PlaceSearchRequest) -> list[PlaceCandidate]:
        """Search for places matching a query."""
        raise NotImplementedError

    @abstractmethod
    async def get_directions(self, request: DirectionsRequest) -> RouteSummary:
        """Compute directions between origin and destination."""
        raise NotImplementedError
