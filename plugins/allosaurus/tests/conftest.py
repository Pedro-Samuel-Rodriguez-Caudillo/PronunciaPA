from __future__ import annotations

import sys
from pathlib import Path

plugin_root = Path(__file__).resolve().parents[1]
if str(plugin_root) not in sys.path:
    sys.path.insert(0, str(plugin_root))
