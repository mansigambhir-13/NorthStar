"""Tests for WebSocket agent chat endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from northstar.web.server import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestWebSocketChat:
    def test_websocket_connect(self, client):
        with client.websocket_connect("/ws/agent") as ws:
            # Just test that connection works
            pass

    def test_websocket_empty_message(self, client):
        with client.websocket_connect("/ws/agent") as ws:
            ws.send_json({"message": ""})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Empty" in data["content"]

    def test_websocket_chat_success(self, client):
        mock_agent = AsyncMock()
        mock_agent.__aenter__ = AsyncMock(return_value=mock_agent)
        mock_agent.__aexit__ = AsyncMock(return_value=None)
        mock_agent.chat = AsyncMock(return_value="Test response")

        with patch("northstar.agent.agent.NorthStarAgent", return_value=mock_agent):
            with client.websocket_connect("/ws/agent") as ws:
                ws.send_json({"message": "hello"})

                tokens = []
                while True:
                    data = ws.receive_json()
                    if data["type"] == "done":
                        break
                    elif data["type"] == "token":
                        tokens.append(data["content"])
                    elif data["type"] == "error":
                        break

                result = "".join(tokens)
                assert result == "Test response"

    def test_websocket_chat_agent_error(self, client):
        mock_agent = AsyncMock()
        mock_agent.__aenter__ = AsyncMock(return_value=mock_agent)
        mock_agent.__aexit__ = AsyncMock(return_value=None)
        mock_agent.chat = AsyncMock(side_effect=Exception("API key invalid"))

        with patch("northstar.agent.agent.NorthStarAgent", return_value=mock_agent):
            with client.websocket_connect("/ws/agent") as ws:
                ws.send_json({"message": "hello"})
                data = ws.receive_json()
                assert data["type"] == "error"
                assert "API key invalid" in data["content"]
