from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from starlette import status

from src.api.config import get_settings
from src.api.errors import AppError
from src.api.models import (
    DirectionsRequest,
    DirectionsResponse,
    LocationQARequest,
    LocationQAResponse,
    PlaceSearchRequest,
    PlaceSearchResponse,
    VoiceCommandRequest,
    VoiceCommandResponse,
)
from src.api.providers.maps.factory import get_maps_provider
from src.api.services.voice import (
    answer_location_qa,
    build_directions_request,
    build_place_search_request,
    parse_voice_command,
)
from src.api.session_store import InMemorySessionStore

router = APIRouter(tags=["assistant"])


def _get_session_store() -> InMemorySessionStore | None:
    settings = get_settings()
    if not settings.enable_sessions:
        return None
    # Module-level singleton is okay for dev; keep it simple.
    # FastAPI may reload; in that case it will reset sessions.
    global _SESSION_STORE  # type: ignore  # noqa: PLW0603
    try:
        store = _SESSION_STORE  # type: ignore  # noqa: F821
    except Exception:
        store = InMemorySessionStore(ttl_seconds=settings.session_ttl_seconds)
        _SESSION_STORE = store  # type: ignore  # noqa: F821
    return store


@router.get(
    "/docs/usage",
    summary="API usage help",
    description="Quick usage notes for the REST API endpoints.",
    tags=["docs"],
)
def usage_help() -> dict:
    """Return short usage documentation for client developers."""
    return {
        "endpoints": {
            "POST /v1/voice/command": "Process a transcribed voice command and return an action + assistant text.",
            "POST /v1/places/search": "Search for places by query.",
            "POST /v1/directions": "Get directions between origin and destination.",
            "POST /v1/location/qa": "Ask a location-based question (basic template answer).",
        },
        "notes": [
            "If GOOGLE_MAPS_API_KEY is not set, the backend will use a mock maps provider.",
            "For directions, provide origin/destination either as coordinates or free-text query.",
        ],
    }


@router.post(
    "/v1/voice/command",
    response_model=VoiceCommandResponse,
    summary="Process a voice command",
    description="Parse a transcribed voice command and optionally call maps APIs to fulfill it.",
    operation_id="processVoiceCommand",
)
async def process_voice_command(payload: VoiceCommandRequest) -> VoiceCommandResponse:
    """Process a transcribed voice command and return a structured action.

    Args:
        payload: VoiceCommandRequest with transcribed text and optional user location/session id.

    Returns:
        VoiceCommandResponse: action, assistant message, and optional structured data.
    """
    settings = get_settings()
    provider = get_maps_provider(settings)
    store = _get_session_store()

    session_id = payload.session_id
    if store:
        session = store.get_or_create(payload.session_id)
        session_id = session.session_id
        store.append_message(session_id, "user", payload.text)

    action = parse_voice_command(payload.text, payload.user_location)

    assistant_text = ""
    data = None

    if action.type == "search_places":
        req = build_place_search_request(action, payload.user_location)
        candidates = await provider.search_places(req)
        assistant_text = f"I found {len(candidates)} place(s) for “{req.query}”."
        data = {"candidates": [c.model_dump() for c in candidates]}

    elif action.type == "get_directions":
        req = build_directions_request(action, payload.user_location)
        # Validate destination presence for directions
        if not req.destination and not req.destination_query:
            raise AppError(
                code="missing_destination",
                message="Please specify where you want to go (e.g., 'navigate to Golden Gate Bridge').",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        route = await provider.get_directions(req)
        assistant_text = f"Route ready. Distance {route.distance_meters} m, ETA {route.duration_seconds} s."
        data = {"route": route.model_dump()}

    elif action.type == "location_qa":
        assistant_text = answer_location_qa(action.query or payload.text, context={"location": payload.user_location.model_dump() if payload.user_location else None})
        data = {"type": "location_qa"}

    else:
        assistant_text = (
            "I didn't understand that yet. Try 'find coffee near me' or 'navigate to <destination>'."
        )
        data = {"type": "unknown"}

    if store and session_id:
        store.append_message(session_id, "assistant", assistant_text, extra={"action": action.model_dump()})

    return VoiceCommandResponse(
        session_id=session_id or "no-session",
        transcript=payload.text,
        action=action,
        assistant_text=assistant_text,
        data=data,
    )


@router.post(
    "/v1/places/search",
    response_model=PlaceSearchResponse,
    summary="Search places",
    description="Search for places by free text query. Uses Google Maps if configured; otherwise a mock provider.",
    operation_id="searchPlaces",
)
async def search_places(payload: PlaceSearchRequest) -> PlaceSearchResponse:
    """Search places by query."""
    settings = get_settings()
    provider = get_maps_provider(settings)
    candidates = await provider.search_places(payload)
    return PlaceSearchResponse(query=payload.query, candidates=candidates)


@router.post(
    "/v1/directions",
    response_model=DirectionsResponse,
    summary="Get directions",
    description="Compute directions between origin and destination using Google Directions API (or a mock provider).",
    operation_id="getDirections",
)
async def get_directions(payload: DirectionsRequest) -> DirectionsResponse:
    """Get directions between origin and destination."""
    settings = get_settings()
    provider = get_maps_provider(settings)

    if not payload.destination and not payload.destination_query:
        raise AppError(code="missing_destination", message="Destination is required.", http_status=400)
    if not payload.origin and not payload.origin_query:
        raise AppError(code="missing_origin", message="Origin is required.", http_status=400)

    route = await provider.get_directions(payload)
    origin_desc = payload.origin_query or (f"{payload.origin.lat},{payload.origin.lng}" if payload.origin else "origin")
    dest_desc = payload.destination_query or (
        f"{payload.destination.lat},{payload.destination.lng}" if payload.destination else "destination"
    )
    return DirectionsResponse(origin=origin_desc, destination=dest_desc, mode=payload.mode, route=route)


@router.post(
    "/v1/location/qa",
    response_model=LocationQAResponse,
    summary="Location-based Q&A",
    description="Answer a location-based question. Currently returns a safe template response (no live data).",
    operation_id="locationQA",
)
async def location_qa(payload: LocationQARequest) -> LocationQAResponse:
    """Answer a location-based question with a safe, non-hallucinating template."""
    context = {
        "location": payload.location.model_dump() if payload.location else None,
        "place_id": payload.place_id,
    }
    answer = answer_location_qa(payload.question, context=context)
    return LocationQAResponse(answer=answer, citations=[], context=context)


@router.get(
    "/v1/provider",
    summary="Provider status",
    description="Returns which maps provider is active (google vs mock).",
    operation_id="providerStatus",
    tags=["assistant"],
)
async def provider_status() -> JSONResponse:
    """Return which provider is selected based on environment configuration."""
    settings = get_settings()
    provider_name = "google" if settings.google_maps_api_key else "mock"
    return JSONResponse(content={"ok": True, "provider": provider_name})
