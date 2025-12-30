"""Smoke tests for the API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from ipa_server.main import get_app

client = TestClient(get_app())


def test_api_health_smoke():
    """Verify the API health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_docs_smoke():
    """Verify the API documentation endpoint exists."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text
