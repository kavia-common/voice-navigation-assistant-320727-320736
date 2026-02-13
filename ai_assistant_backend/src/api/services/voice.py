from __future__ import annotations

import re
from typing import Any

from src.api.errors import AppError
from src.api.models import DirectionsRequest, LatLng, PlaceSearchRequest, VoiceCommandAction


def _maybe_latlng_from_text(text: str) -> LatLng | None:
    """Extract a `lat,lng` pair from text if present (very lightweight)."""
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", text)
    if not m:
        return None
    try:
        return LatLng(lat=float(m.group(1)), lng=float(m.group(2)))
    except Exception:
        return None


# PUBLIC_INTERFACE
def parse_voice_command(text: str, user_location: LatLng | None) -> VoiceCommandAction:
    """Parse a voice command into a normalized action.

    This is a rule-based parser intended as a baseline; it can be replaced with an LLM later.

    Args:
        text: Transcribed voice command.
        user_location: Optional current user location.

    Returns:
        VoiceCommandAction: normalized action type and extracted parameters.
    """
    t = text.strip().lower()
    if not t:
        raise AppError(code="empty_command", message="Command text is empty.", http_status=400)

    # Directions intents
    if any(k in t for k in ["directions", "navigate", "route", "go to", "take me to"]):
        # Try "to X"
        dest_query = None
        m = re.search(r"\bto\s+(.+)$", t)
        if m:
            dest_query = m.group(1).strip()
        dest_ll = _maybe_latlng_from_text(t)

        return VoiceCommandAction(
            type="get_directions",
            query=None,
            origin=user_location,
            destination_query=dest_query if (dest_query and not dest_ll) else None,
            destination=dest_ll,
        )

    # Place search intents
    if any(k in t for k in ["find", "search", "nearby", "near me", "closest", "coffee", "restaurant", "gas"]):
        q = text.strip()
        return VoiceCommandAction(type="search_places", query=q, origin=None, destination_query=None, destination=None)

    # Location Q&A intents
    if any(k in t for k in ["what is", "what's", "how far", "hours", "open", "tell me about"]):
        return VoiceCommandAction(type="location_qa", query=text.strip(), origin=None, destination_query=None, destination=None)

    return VoiceCommandAction(type="unknown", query=text.strip(), origin=None, destination_query=None, destination=None)


# PUBLIC_INTERFACE
def build_place_search_request(action: VoiceCommandAction, user_location: LatLng | None) -> PlaceSearchRequest:
    """Convert an action into a PlaceSearchRequest."""
    if action.type != "search_places":
        raise AppError(code="invalid_action", message="Action is not search_places.", http_status=400)
    if not action.query:
        raise AppError(code="missing_query", message="Search query is missing.", http_status=400)
    return PlaceSearchRequest(query=action.query, near=user_location, radius_meters=3000, limit=5)


# PUBLIC_INTERFACE
def build_directions_request(action: VoiceCommandAction, user_location: LatLng | None) -> DirectionsRequest:
    """Convert an action into a DirectionsRequest."""
    if action.type != "get_directions":
        raise AppError(code="invalid_action", message="Action is not get_directions.", http_status=400)

    return DirectionsRequest(
        origin=action.origin or user_location,
        destination=action.destination,
        destination_query=action.destination_query,
        mode="driving",
    )


# PUBLIC_INTERFACE
def answer_location_qa(question: str, context: dict[str, Any] | None = None) -> str:
    """Return a simple, safe answer for a location-based question.

    Without an LLM/search integration, we respond with a constrained template.
    """
    q = question.strip()
    if not q:
        raise AppError(code="missing_question", message="Question is required.", http_status=400)

    if context and context.get("place_name"):
        return f"I don't have live details, but you asked about {context['place_name']}: “{q}”."
    if context and context.get("location"):
        return f"I don't have live details, but for that location you asked: “{q}”."
    return f"I don't have live details yet, but I can help with directions or place search. You asked: “{q}”."
