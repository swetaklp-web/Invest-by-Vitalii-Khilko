from __future__ import annotations

from typing import Literal
from uuid import uuid4

from app.ai.generate_post import generate_post
from app.ai.quality_check import check_post
from app.design.render_image import render_market_card
from app.sources.manual_inputs import load_manual_inputs
from app.storage.drafts import create_draft


def build_draft(
    post_type: Literal["morning_brief", "evening_theme"],
    revision: Literal["shorter", "deeper"] | None = None,
    previous_post: dict | None = None,
) -> dict:
    post = generate_post(load_manual_inputs(), post_type, revision, previous_post)
    quality = check_post(post)
    temporary_id = uuid4().hex[:12]
    image_path = render_market_card(post, temporary_id)
    draft = create_draft(post, quality, image_path)
    final_image_path = image_path.with_name(f"{draft['id']}.png")
    image_path.replace(final_image_path)
    draft["image_path"] = str(final_image_path)
    from app.storage.drafts import save_draft

    save_draft(draft)
    return draft
