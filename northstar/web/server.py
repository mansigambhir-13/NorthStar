"""FastAPI application factory for NorthStar web dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from northstar import __version__


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="NorthStar Dashboard",
        description="Priority Debt Engine — Web Dashboard",
        version=__version__,
    )

    # Import and register routers
    from northstar.web.api import router as api_router
    from northstar.web.ws import router as ws_router

    app.include_router(api_router)
    app.include_router(ws_router)

    # Serve static files (frontend SPA)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
