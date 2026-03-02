"""Tests for the FastAPI app factory."""

from __future__ import annotations

import pytest
from fastapi import FastAPI


def test_create_app_returns_fastapi():
    from northstar.web.server import create_app

    app = create_app()
    assert isinstance(app, FastAPI)


def test_create_app_has_api_routes():
    from northstar.web.server import create_app

    app = create_app()
    paths = [r.path for r in app.routes]
    assert "/api/status" in paths
    assert "/api/tasks" in paths
    assert "/api/pds" in paths


def test_create_app_has_websocket_route():
    from northstar.web.server import create_app

    app = create_app()
    paths = [r.path for r in app.routes]
    assert "/ws/agent" in paths


def test_create_app_metadata():
    from northstar.web.server import create_app

    app = create_app()
    assert app.title == "NorthStar Dashboard"
    assert "0.1.0" in app.version
