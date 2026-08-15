"""Tests for FastAPI HTTP endpoints and WebSocket server."""

import pytest
from fastapi.testclient import TestClient
from linuxextend import server as server_module


@pytest.fixture
def client():
    return TestClient(server_module.app)


def test_root_html_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "LinuxExtend" in response.text
    assert "screenCanvas" in response.text
    assert "WebSocket" in response.text


def test_status_endpoint(client):
    server_module.display_info = {"name": "HEADLESS-1", "resolution": "1920x1080"}
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["display"]["name"] == "HEADLESS-1"
    assert "capture" in data
    assert "clients" in data
