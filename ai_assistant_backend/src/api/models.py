from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class LatLng(BaseModel):
    """Geographic coordinates."""

    lat: float = Field(..., description="Latitude in decimal degrees.", ge=-90, le=90)
    lng: float = Field(..., description="Longitude in decimal degrees.", ge=-180, le=180)


class ApiError(BaseModel):
    """Standard error response envelope."""

    code: str = Field(..., description="Stable, machine-readable error code.")
    message: str = Field(..., description="Human-readable error message.")
    details: dict[str, Any] | None = Field(default=None, description="Optional additional error details.")


class Envelope(BaseModel):
    """Standard success response envelope."""

    ok: bool = Field(True, description="Always true for success responses.")


class PlaceCandidate(BaseModel):
    """Place candidate returned from search."""

    place_id: str = Field(..., description="Provider-specific place identifier.")
    name: str = Field(..., description="Display name of the place.")
    address: str | None = Field(default=None, description="Formatted address if available.")
    location: LatLng | None = Field(default=None, description="Best-known coordinates for the place.")
    types: list[str] = Field(default_factory=list, description="Provider place types/categories.")


class RouteStep(BaseModel):
    """Navigation step."""

    instruction: str = Field(..., description="Turn-by-turn instruction (plain text).")
    distance_meters: int | None = Field(default=None, description="Step distance in meters.", ge=0)
    duration_seconds: int | None = Field(default=None, description="Step duration in seconds.", ge=0)


class RouteSummary(BaseModel):
    """High-level route summary."""

    distance_meters: int = Field(..., description="Total route distance in meters.", ge=0)
    duration_seconds: int = Field(..., description="Estimated duration in seconds.", ge=0)
    polyline: str | None = Field(default=None, description="Encoded polyline if provided by provider.")
    steps: list[RouteStep] = Field(default_factory=list, description="Ordered route steps.")


class VoiceCommandRequest(BaseModel):
    """Request to process a voice command (already transcribed to text on client)."""

    text: str = Field(..., description="Transcribed voice command text.", min_length=1, max_length=2000)
    session_id: str | None = Field(
        default=None,
        description="Optional conversation/session id. If omitted, server may create one.",
        max_length=128,
    )
    user_location: LatLng | None = Field(
        default=None, description="Optional user's current location to interpret commands."
    )


class VoiceCommandAction(BaseModel):
    """Normalized action predicted from voice command text."""

    type: Literal["search_places", "get_directions", "location_qa", "unknown"] = Field(
        ..., description="Action type."
    )
    query: str | None = Field(default=None, description="Search query / QA question.")
    origin: LatLng | None = Field(default=None, description="Directions origin, if known.")
    destination_query: str | None = Field(default=None, description="Destination name/address for directions.")
    destination: LatLng | None = Field(default=None, description="Destination coordinates for directions.")


class VoiceCommandResponse(Envelope):
    """Response returned for a processed voice command."""

    session_id: str = Field(..., description="Session id used for this conversation.")
    transcript: str = Field(..., description="Echo of the command text.")
    action: VoiceCommandAction = Field(..., description="Normalized action prediction.")
    assistant_text: str = Field(..., description="Assistant message suitable for TTS/UI display.")
    data: dict[str, Any] | None = Field(
        default=None, description="Optional action-specific structured payload."
    )


class PlaceSearchRequest(BaseModel):
    """Request for place search."""

    query: str = Field(..., description="Free text query, e.g., 'coffee near me'.", min_length=1, max_length=512)
    near: LatLng | None = Field(default=None, description="Optional center point for nearby search bias.")
    radius_meters: int | None = Field(
        default=3000, description="Optional radius for nearby bias (meters).", ge=1, le=50000
    )
    limit: int = Field(default=5, description="Maximum number of candidates to return.", ge=1, le=20)

    @field_validator("query")
    @classmethod
    def _strip_query(cls, v: str) -> str:
        v2 = v.strip()
        if not v2:
            raise ValueError("query must not be empty")
        return v2


class PlaceSearchResponse(Envelope):
    """Response for place search."""

    query: str = Field(..., description="Echo of the query.")
    candidates: list[PlaceCandidate] = Field(default_factory=list, description="Place candidates.")


class DirectionsRequest(BaseModel):
    """Request for directions."""

    origin: LatLng | None = Field(default=None, description="Origin coordinates.")
    origin_query: str | None = Field(default=None, description="Origin as free text (address/place).")
    destination: LatLng | None = Field(default=None, description="Destination coordinates.")
    destination_query: str | None = Field(default=None, description="Destination as free text (address/place).")
    mode: Literal["driving", "walking", "bicycling", "transit"] = Field(
        default="driving", description="Travel mode."
    )

    @field_validator("destination_query")
    @classmethod
    def _strip_dest_query(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v

    @field_validator("origin_query")
    @classmethod
    def _strip_origin_query(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v


class DirectionsResponse(Envelope):
    """Response for directions."""

    origin: str = Field(..., description="Resolved origin description.")
    destination: str = Field(..., description="Resolved destination description.")
    mode: str = Field(..., description="Mode used for routing.")
    route: RouteSummary = Field(..., description="Route summary.")


class LocationQARequest(BaseModel):
    """Ask a question about a location or area."""

    question: str = Field(..., description="The user's question.", min_length=1, max_length=1000)
    location: LatLng | None = Field(default=None, description="Location context for the question.")
    place_id: str | None = Field(default=None, description="Optional place_id context.", max_length=128)

    @field_validator("question")
    @classmethod
    def _strip_question(cls, v: str) -> str:
        v2 = v.strip()
        if not v2:
            raise ValueError("question must not be empty")
        return v2


class LocationQAResponse(Envelope):
    """Response for location-based Q&A."""

    answer: str = Field(..., description="Assistant's answer.")
    citations: list[str] = Field(default_factory=list, description="Optional citations/links.")
    context: dict[str, Any] | None = Field(default=None, description="Optional structured context used.")
