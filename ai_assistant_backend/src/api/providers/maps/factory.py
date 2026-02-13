from __future__ import annotations

from src.api.config import Settings
from src.api.providers.maps.base import MapsProvider
from src.api.providers.maps.google import GoogleMapsProvider
from src.api.providers.maps.mock import MockMapsProvider


# PUBLIC_INTERFACE
def get_maps_provider(settings: Settings) -> MapsProvider:
    """Return a maps provider instance based on configuration.

    If GOOGLE_MAPS_API_KEY is absent, returns a safe MockMapsProvider.
    """
    if settings.google_maps_api_key:
        return GoogleMapsProvider(settings)
    return MockMapsProvider()
