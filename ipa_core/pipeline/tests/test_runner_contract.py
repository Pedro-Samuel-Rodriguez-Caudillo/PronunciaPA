"""Pruebas de contrato del runner del pipeline (stub)."""
from __future__ import annotations

import pytest

from ipa_core.pipeline import runner


def test_run_pipeline_is_stub() -> None:
    assert hasattr(runner, "run_pipeline")
    with pytest.raises(NotImplementedError):
        # Llamada mínima contraria a ejecutar: fuerza la excepción del stub
        runner.run_pipeline(  # type: ignore[arg-type]
            pre=None,  # stubs: no se instancian implementaciones
            asr=None,
            textref=None,
            comp=None,
            audio={"path": "", "sample_rate": 0, "channels": 0},
            text="",
        )

