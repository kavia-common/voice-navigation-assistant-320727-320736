from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import get_settings
from src.api.errors import install_exception_handlers
from src.api.routes import router as assistant_router

settings = get_settings()

openapi_tags = [
    {"name": "assistant", "description": "Voice assistant, places search, and navigation endpoints."},
    {"name": "docs", "description": "Developer documentation helpers."},
]

app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    openapi_tags=openapi_tags,
)

install_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["assistant"], summary="Health check", operation_id="healthCheck")
def health_check() -> dict:
    """Health check endpoint.

    Returns:
        dict: Simple status payload.
    """
    return {"ok": True, "message": "Healthy"}


app.include_router(assistant_router)
