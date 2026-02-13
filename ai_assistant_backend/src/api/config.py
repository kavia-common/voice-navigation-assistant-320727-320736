from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables.

    Note: the backend container's .env currently lists REACT_APP_* vars only.
    We still support GOOGLE_MAPS_API_KEY if present in runtime environment.
    """

    app_title: str = "AI Voice Navigation Assistant API"
    app_description: str = (
        "Backend for an AI voice navigation assistant. Provides endpoints to parse voice commands, "
        "search places, compute directions, and answer location-based questions."
    )
    app_version: str = "0.2.0"

    # CORS: keep permissive defaults for dev; can be restricted via env var.
    cors_allow_origins: tuple[str, ...] = ("*",)

    # Provider config
    google_maps_api_key: str | None = None
    google_maps_base_url: str = "https://maps.googleapis.com/maps/api"

    # Simple in-memory conversation/session state (optional)
    enable_sessions: bool = True
    session_ttl_seconds: int = 60 * 30  # 30 minutes


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load settings from environment variables.

    Returns:
        Settings: Parsed settings object.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or None
    cors_origins_raw = os.getenv("CORS_ALLOW_ORIGINS")  # comma-separated list
    if cors_origins_raw:
        origins = tuple(o.strip() for o in cors_origins_raw.split(",") if o.strip())
    else:
        origins = ("*",)

    enable_sessions = os.getenv("ENABLE_SESSIONS", "true").strip().lower() in {"1", "true", "yes", "on"}
    ttl_str = os.getenv("SESSION_TTL_SECONDS")
    ttl = int(ttl_str) if (ttl_str and ttl_str.isdigit()) else 60 * 30

    return Settings(
        cors_allow_origins=origins,
        google_maps_api_key=api_key,
        enable_sessions=enable_sessions,
        session_ttl_seconds=ttl,
    )
