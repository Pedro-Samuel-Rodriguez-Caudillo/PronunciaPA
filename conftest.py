from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


if importlib.util.find_spec("pytest_benchmark") is None:
    @pytest.fixture
    def benchmark():
        pytest.skip("pytest-benchmark not installed")
