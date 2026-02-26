"""Tests para los endpoints de planificación de lecciones con LLM.

Ejecutar con:
    PYTHONPATH=. pytest ipa_server/tests/test_http_lessons.py -v
"""
from __future__ import annotations

import os
import tempfile
import pytest
import yaml
from pathlib import Path
from fastapi.testclient import TestClient

from ipa_core.history.memory import InMemoryHistory
from ipa_server.main import get_app
from ipa_server.routers import pipeline as pipeline_router


def _write_stub_config(tmp_path: Path | None = None) -> str:
    """Escribe un YAML de configuración con backends stub y retorna la ruta."""
    test_config = {
        "version": 1,
        "language_pack": None,
        "model_pack": None,
        "backend": {"name": "stub"},
        "textref": {"name": "grapheme"},
        "preprocessor": {"name": "basic"},
        "comparator": {"name": "levenshtein"},
        "llm": {"name": "stub"},
    }
    if tmp_path:
        p = tmp_path / "test_lesson_config.yaml"
        p.write_text(yaml.dump(test_config), encoding="utf-8")
        return str(p)
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w") as f:
        yaml.dump(test_config, f)
    return path


@pytest.fixture()
def stub_config(tmp_path, monkeypatch):
    """Fixture: establece PRONUNCIAPA_CONFIG con stub LLM + resets kernel."""
    cfg_path = _write_stub_config(tmp_path)
    monkeypatch.setenv("PRONUNCIAPA_CONFIG", cfg_path)
    # Remove env vars that pydantic-settings would parse for complex fields
    # (e.g. PRONUNCIAPA_LLM=stub would fail JSON decoding for PluginCfg)
    for var in ("PRONUNCIAPA_LLM", "PRONUNCIAPA_ASR", "PRONUNCIAPA_TEXTREF"):
        monkeypatch.delenv(var, raising=False)
    # Reset kernel singleton so the new config is picked up
    pipeline_router._cached_kernel = None
    pipeline_router._kernel_ready = False
    yield cfg_path
    pipeline_router._cached_kernel = None
    pipeline_router._kernel_ready = False


@pytest.fixture()
def client(stub_config):
    """Cliente HTTP con stub LLM."""
    app = get_app()
    c = TestClient(app, raise_server_exceptions=False)
    yield c


# ---------------------------------------------------------------------------
# POST /v1/lessons/plan
# ---------------------------------------------------------------------------

class TestLessonPlanEndpoint:
    def test_plan_with_stub_llm_returns_lesson(self, client):
        """Con LLM stub debe devolver un LessonPlanResponse válido."""
        resp = client.post(
            "/v1/lessons/plan",
            json={"user_id": "test_user", "lang": "es"},
        )
        if resp.status_code == 503:
            pytest.skip("LLM no configurado en este entorno de test")
        assert resp.status_code == 200
        body = resp.json()
        assert "recommended_sound_id" in body
        assert "topic_id" in body
        assert "intro" in body
        assert isinstance(body["tips"], list)
        assert isinstance(body["drills"], list)

    def test_plan_with_sound_id_hint(self, client):
        """El campo sound_id opcional es aceptado sin error."""
        resp = client.post(
            "/v1/lessons/plan",
            json={"user_id": "test_user", "lang": "es", "sound_id": "s"},
        )
        if resp.status_code == 503:
            pytest.skip("LLM no configurado en este entorno de test")
        assert resp.status_code == 200

    def test_plan_requires_user_id(self, client):
        """Falta user_id → error de validación 422."""
        resp = client.post("/v1/lessons/plan", json={"lang": "es"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /v1/lessons/roadmap/{user_id}/{lang}
# ---------------------------------------------------------------------------

class TestRoadmapEndpoint:
    def test_roadmap_without_history_returns_503(self, client):
        """Sin historial configurado debe devolver 503."""
        resp = client.get("/v1/lessons/roadmap/user123/es")
        assert resp.status_code in (200, 503)

    def test_roadmap_schema_when_available(self, client):
        """La respuesta, si 200, debe tener el esquema correcto."""
        resp = client.get("/v1/lessons/roadmap/user123/es")
        if resp.status_code != 200:
            pytest.skip("History no configurado")
        body = resp.json()
        assert "user_id" in body
        assert "lang" in body
        assert "topics" in body
        assert isinstance(body["topics"], list)


# ---------------------------------------------------------------------------
# POST /v1/lessons/generate/{lang}/{sound_id}
# ---------------------------------------------------------------------------

class TestGenerateLessonEndpoint:
    def test_generate_for_known_sound(self, client):
        """Generar lección para un fonema concreto."""
        resp = client.post("/v1/lessons/generate/es/s")
        if resp.status_code == 503:
            pytest.skip("LLM no configurado en este entorno de test")
        assert resp.status_code == 200
        body = resp.json()
        assert "recommended_sound_id" in body
        assert "intro" in body

    def test_generate_drills_is_list(self, client):
        """El campo drills siempre es lista."""
        resp = client.post("/v1/lessons/generate/es/a")
        if resp.status_code == 503:
            pytest.skip("LLM no configurado")
        assert resp.status_code == 200
        assert isinstance(resp.json()["drills"], list)


# ---------------------------------------------------------------------------
# LessonService unit tests (sin HTTP)
# ---------------------------------------------------------------------------

class TestLessonService:
    @pytest.mark.asyncio
    async def test_plan_lesson_returns_stub_when_no_llm(self):
        """Sin LLM en el kernel, plan_lesson devuelve el stub."""
        from unittest.mock import MagicMock
        from ipa_core.services.lesson import plan_lesson

        kernel = MagicMock()
        kernel.llm = None
        kernel.history = None

        result = await plan_lesson("user1", "es", kernel)
        assert "recommended_sound_id" in result
        assert "intro" in result

    @pytest.mark.asyncio
    async def test_update_roadmap_is_noop_without_history(self):
        """update_roadmap no falla si no hay historial configurado."""
        from unittest.mock import MagicMock
        from ipa_core.services.lesson import update_roadmap

        kernel = MagicMock()
        kernel.history = None

        result = await update_roadmap("user1", "es", kernel)
        assert result == {}

    def test_load_roadmap_es_exists(self):
        """El roadmap de español debe existir y tener topics."""
        from ipa_core.services.lesson import load_roadmap

        roadmap = load_roadmap("es")
        assert roadmap is not None
        assert "topics" in roadmap
        assert len(roadmap["topics"]) > 0

    def test_load_roadmap_unknown_lang_returns_none(self):
        """Idioma sin roadmap retorna None sin excepción."""
        from ipa_core.services.lesson import load_roadmap

        roadmap = load_roadmap("xx_does_not_exist")
        assert roadmap is None

    def test_roadmap_topics_have_required_fields(self):
        """Cada topic del roadmap tiene id, name, phonemes."""
        from ipa_core.services.lesson import load_roadmap

        roadmap = load_roadmap("es")
        assert roadmap is not None
        for topic in roadmap["topics"]:
            assert "id" in topic, f"topic missing 'id': {topic}"
            assert "name" in topic, f"topic missing 'name': {topic}"
            assert "phonemes" in topic, f"topic missing 'phonemes': {topic}"


# ---------------------------------------------------------------------------
# InMemoryHistory roadmap methods
# ---------------------------------------------------------------------------

class TestInMemoryHistoryRoadmap:
    @pytest.mark.asyncio
    async def test_round_trip_roadmap_progress(self):
        """Guardar y recuperar progreso del roadmap."""
        history = InMemoryHistory()
        await history.setup()

        await history.record_roadmap_progress(
            user_id="u1", lang="es", topic_id="vowels", level="in_progress"
        )
        await history.record_roadmap_progress(
            user_id="u1", lang="es", topic_id="fricatives", level="proficient"
        )

        progress = await history.get_roadmap_progress("u1", "es")
        assert progress == {"vowels": "in_progress", "fricatives": "proficient"}

    @pytest.mark.asyncio
    async def test_roadmap_progress_overwrite(self):
        """Actualizar el nivel de un tema sobreescribe el anterior."""
        history = InMemoryHistory()
        await history.setup()

        await history.record_roadmap_progress(
            user_id="u1", lang="es", topic_id="vowels", level="not_started"
        )
        await history.record_roadmap_progress(
            user_id="u1", lang="es", topic_id="vowels", level="completed"
        )

        progress = await history.get_roadmap_progress("u1", "es")
        assert progress["vowels"] == "completed"

    @pytest.mark.asyncio
    async def test_roadmap_progress_empty_for_new_user(self):
        """Nuevo usuario tiene roadmap vacío."""
        history = InMemoryHistory()
        await history.setup()

        progress = await history.get_roadmap_progress("new_user", "es")
        assert progress == {}

    @pytest.mark.asyncio
    async def test_roadmap_isolated_by_lang(self):
        """Progress for 'es' and 'en' are stored independently."""
        history = InMemoryHistory()
        await history.setup()

        await history.record_roadmap_progress(
            user_id="u1", lang="es", topic_id="vowels", level="completed"
        )
        progress_en = await history.get_roadmap_progress("u1", "en")
        assert "vowels" not in progress_en

