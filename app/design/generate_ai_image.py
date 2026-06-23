from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.config import ROOT_DIR, settings
from app.design.visual_policy import load_visual_policy, select_visual_type


def _image_prompt(post: dict[str, Any], variant_number: int) -> str:
    tickers = ", ".join(post.get("tickers", [])[:5]) or "US market"
    source_context = " ".join(
        str(source.get("summary", "")) for source in post.get("sources", [])[:3]
    )
    policy = load_visual_policy()
    visual_type = select_visual_type(variant_number)
    avoid = "; ".join(str(item) for item in policy.get("avoid", [])[:10])
    hard_rules = " ".join(str(item) for item in policy.get("hard_rules", [])[:8])
    composition_rule = (
        "Use a noticeably different composition, camera angle, layout and visual metaphor "
        f"for variant #{variant_number}. Do not solve the variation by changing only colors."
    )
    return (
        "Create one professional editorial image for a Russian-language investment Telegram post. "
        "The image must be highly realistic by default: photorealistic, documentary, premium editorial, "
        "with real-world lighting, physical materials, depth of field and credible financial context. "
        "It should feel native to a serious investment Telegram channel: evidence-first, market-aware, "
        "closer to a polished market screenshot, product context, company/sector scene or analytical "
        "visual essay than to a flat fintech card or a cartoon illustration. "
        f"News topic: {post.get('image_title') or post.get('title')}. "
        f"Verified context: {source_context}. Related tickers: {tickers}. "
        f"Visual type: {visual_type['name']}. Direction: {visual_type['direction']}. "
        "Premium editorial quality, realistic detail, credible financial atmosphere, clean hierarchy, "
        "high production value, not generic, not simplistic, not a template. "
        "Taboo: cartoon people, cute mascots, toy-like 3D characters, egg-shaped smooth characters, "
        "flat childish illustration style, pseudo-Pixar style. "
        f"{composition_rule} "
        f"Hard rules: {hard_rules} Avoid: {avoid}."
    )


def _image_size(variant_number: int) -> str:
    return select_visual_type(variant_number)["size"]


def generate_ai_news_image(
    post: dict[str, Any], draft_id: str, variant_number: int = 1
) -> Path:
    settings.require("openai_api_key")
    output_path = ROOT_DIR / "data" / "drafts" / f"{draft_id}-ai-{variant_number}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.images.generate(
        model=settings.openai_image_model,
        prompt=_image_prompt(post, variant_number),
        size=_image_size(variant_number),
        quality="medium",
        n=1,
    )
    image = response.data[0]
    if not image.b64_json:
        raise RuntimeError("OpenAI image generation returned no image data")
    output_path.write_bytes(base64.b64decode(image.b64_json))
    return output_path
