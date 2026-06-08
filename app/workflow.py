from __future__ import annotations

from typing import Literal
from uuid import uuid4

from app.ai.generate_post import generate_post
from app.ai.quality_check import check_post
from app.config import settings
from app.design.render_image import render_market_card
from app.sources.barchart import fetch_barchart_signals
from app.sources.manual_inputs import load_manual_inputs
from app.sources.oninvest import fetch_oninvest_signals
from app.sources.telegram_reader import fetch_telegram_signals
from app.sources.x_reader import fetch_x_signals
from app.sources.yahoo import fetch_yahoo_signals
from app.storage.drafts import create_draft
from app.storage.logs import write_log


def load_source_inputs(post_type: str) -> dict:
    inputs = load_manual_inputs()
    inputs.setdefault("signals", [])
    missing_optional = settings.missing_optional_env_vars()
    if missing_optional:
        write_log(
            {
                "post_type": post_type,
                "status": "warning",
                "warning": "Optional API keys are missing; using data/manual_inputs.json",
                "missing_optional_env_vars": missing_optional,
                "source_mode": "manual_inputs",
            }
        )
    adapters = (
        ("x", fetch_x_signals),
        ("yahoo", fetch_yahoo_signals),
        ("barchart", fetch_barchart_signals),
        ("telegram", fetch_telegram_signals),
        ("oninvest", fetch_oninvest_signals),
    )
    external_count = 0
    for source_name, fetcher in adapters:
        try:
            signals = fetcher()
            inputs["signals"].extend(signals)
            external_count += len(signals)
            write_log(
                {
                    "post_type": post_type,
                    "status": "source_checked",
                    "source": source_name,
                    "signals_found": len(signals),
                }
            )
        except Exception as error:
            write_log(
                {
                    "post_type": post_type,
                    "status": "source_warning",
                    "source": source_name,
                    "error": str(error),
                    "fallback": "manual_inputs",
                }
            )
    inputs["source_mode"] = "hybrid" if external_count else "manual_inputs"
    return inputs


def build_draft(
    post_type: Literal["morning_brief", "evening_theme"],
    revision: Literal["shorter", "deeper"] | None = None,
    previous_post: dict | None = None,
) -> dict:
    inputs = load_source_inputs(post_type)
    post = generate_post(inputs, post_type, revision, previous_post)
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
