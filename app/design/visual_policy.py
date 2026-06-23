from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.config import ROOT_DIR


DEFAULT_VISUAL_TYPES: tuple[dict[str, str], ...] = (
    {
        "name": "market_terminal",
        "size": "1536x1024",
        "direction": (
            "realistic market terminal scene with abstract charts, candlesticks, "
            "capital flow panels and no readable labels"
        ),
    },
    {
        "name": "company_product_context",
        "size": "1536x1024",
        "direction": (
            "editorial product or industry context scene connected to the company "
            "or sector, without invented logos"
        ),
    },
    {
        "name": "ecosystem_map",
        "size": "1024x1024",
        "direction": (
            "textless ecosystem map with sectors, supply chains and capital flows "
            "shown through icons, blocks and arrows"
        ),
    },
)


@lru_cache(maxsize=1)
def load_visual_policy() -> dict[str, Any]:
    path = ROOT_DIR / "data" / "visual_policy.json"
    if not path.exists():
        return {"visual_types": list(DEFAULT_VISUAL_TYPES), "hard_rules": [], "avoid": []}
    with path.open("r", encoding="utf-8") as file:
        policy = json.load(file)
    if not policy.get("visual_types"):
        policy["visual_types"] = list(DEFAULT_VISUAL_TYPES)
    return policy


def select_visual_type(variant_number: int) -> dict[str, str]:
    policy = load_visual_policy()
    visual_types = policy.get("visual_types") or list(DEFAULT_VISUAL_TYPES)
    index = (max(variant_number, 1) - 1) % len(visual_types)
    selected = dict(visual_types[index])
    selected.setdefault("name", DEFAULT_VISUAL_TYPES[0]["name"])
    selected.setdefault("size", DEFAULT_VISUAL_TYPES[0]["size"])
    selected.setdefault("direction", DEFAULT_VISUAL_TYPES[0]["direction"])
    return selected
