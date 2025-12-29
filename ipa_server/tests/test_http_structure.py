"""Tests for the HTTP API structure and CORS."""
from __future__ import annotations
import os
import pytest
from fastapi.testclient import TestClient
from ipa_server.main import get_app

def test_health_endpoint() -> None:
    """Verifica que el endpoint /health responde ok."""
    client = TestClient(get_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_cors_headers_with_env(monkeypatch) -> None:
    """Verifica que los headers CORS están presentes según la variable de entorno."""
    monkeypatch.setenv("PRONUNCIAPA_ALLOWED_ORIGINS", "http://localhost:5173,http://example.com")
    client = TestClient(get_app())
    
    # Pre-flight request
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

def test_cors_headers_disallow_origin(monkeypatch) -> None:
    """Verifica que orígenes no permitidos son rechazados por CORS."""
    monkeypatch.setenv("PRONUNCIAPA_ALLOWED_ORIGINS", "http://localhost:5173")
    client = TestClient(get_app())
    
    response = client.options(
        "/health",
        headers={
            "Origin": "http://malicious.com",
            "Access-Control-Request-Method": "GET",
        },
    )
def test_openapi_schema() -> None:
    """Verifica que el schema OpenAPI se genera correctamente."""
    client = TestClient(get_app())
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "ASRResponse" in schema["components"]["schemas"]
    assert "CompareResponse" in schema["components"]["schemas"]
    assert "/v1/transcribe" in schema["paths"]
    assert "/v1/compare" in schema["paths"]

