from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import ROOT_DIR


def load_manual_inputs(path: Path | None = None) -> dict[str, Any]:
    source_path = path or ROOT_DIR / "data" / "manual_inputs.json"
    with source_path.open(encoding="utf-8") as file:
        return json.load(file)
