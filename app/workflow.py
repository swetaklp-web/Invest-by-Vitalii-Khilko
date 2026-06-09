from __future__ import annotations

import re
import time
from typing import Literal
from uuid import uuid4

from app.ai.generate_post import generate_post
from app.ai.fact_check import verify_post_grounding
from app.ai.quality_check import check_post
from app.config import settings
from app.design.render_image import render_market_card
from app.sources.barchart import fetch_barchart_signals
from app.sources.freshness import filter_fresh_signals, today_moscow
from app.sources.manual_inputs import load_manual_inputs
from app.sources.oninvest import fetch_oninvest_signals
from app.sources.telegram_reader import fetch_telegram_signals
from app.sources.x_reader import fetch_x_signals
from app.sources.yahoo import fetch_yahoo_market_snapshot, fetch_yahoo_signals
from app.storage.drafts import create_draft
from app.storage.logs import write_log


class FreshSourceDataUnavailable(RuntimeError):
    pass


def select_alternative_signals(inputs: dict, previous_post: dict | None) -> dict:
    previous_text = str((previous_post or {}).get("telegram_text") or "")
    previous_tickers = set(re.findall(r"\$([A-Z]{1,6})", previous_text))
    signals = list(inputs.get("signals", []))
    alternatives = [
        signal
        for signal in signals
        if previous_tickers.isdisjoint(set(signal.get("tickers", [])))
    ]
    if len(alternatives) < 5:
        alternatives = signals
    inputs["signals"] = alternatives[:25]
    inputs["source_quality"]["alternative_to_tickers"] = sorted(previous_tickers)
    inputs["source_quality"]["alternative_candidates"] = len(inputs["signals"])
    return inputs


def load_source_inputs_with_retries(post_type: str, attempts: int = 3) -> dict:
    last_inputs: dict = {}
    for attempt in range(attempts):
        last_inputs = load_source_inputs(post_type)
        if last_inputs.get("signals"):
            return last_inputs
        if attempt < attempts - 1:
            time.sleep(2)
    return last_inputs


def load_source_inputs(post_type: str) -> dict:
    current_date = today_moscow()
    inputs = load_manual_inputs()
    manual_signals, stale_manual_signals = filter_fresh_signals(inputs.get("signals", []), current_date)
    inputs["date"] = current_date
    inputs["signals"] = manual_signals
    inputs["source_quality"] = {
        "fresh_date": current_date,
        "rule": "Use only signals dated today in Europe/Moscow. Do not infer facts from stale signals.",
        "stale_manual_signals_dropped": len(stale_manual_signals),
    }
    if stale_manual_signals:
        write_log(
            {
                "post_type": post_type,
                "status": "source_warning",
                "source": "manual_inputs",
                "warning": "Stale manual signals dropped",
                "fresh_date": current_date,
                "stale_signals_dropped": len(stale_manual_signals),
            }
        )
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
    try:
        inputs["market_snapshot"] = fetch_yahoo_market_snapshot()
    except Exception as error:
        inputs["market_snapshot"] = {"date": current_date, "quotes": [], "error": str(error)}
        write_log(
            {
                "post_type": post_type,
                "status": "source_warning",
                "source": "yahoo_market_snapshot",
                "error": str(error),
            }
        )
    external_count = 0
    stale_external_count = 0
    for source_name, fetcher in adapters:
        try:
            signals = fetcher()
            fresh_signals, stale_signals = filter_fresh_signals(signals, current_date)
            inputs["signals"].extend(fresh_signals)
            external_count += len(fresh_signals)
            stale_external_count += len(stale_signals)
            write_log(
                {
                    "post_type": post_type,
                    "status": "source_checked",
                    "source": source_name,
                    "signals_found": len(fresh_signals),
                    "stale_signals_dropped": len(stale_signals),
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
    inputs["source_quality"]["fresh_signals_count"] = len(inputs["signals"])
    inputs["source_quality"]["stale_external_signals_dropped"] = stale_external_count
    inputs["source_quality"]["discovery_topics"] = sorted(
        {
            str(signal.get("discovery_query"))
            for signal in inputs["signals"]
            if signal.get("discovery_query")
        }
    )
    inputs["source_quality"]["covered_tickers"] = sorted(
        {
            str(ticker)
            for signal in inputs["signals"]
            for ticker in signal.get("tickers", [])
            if ticker
        }
    )
    inputs["source_mode"] = "fresh_sources" if inputs["signals"] else "market_snapshot_only"
    return inputs


def build_draft(
    post_type: Literal["morning_brief", "evening_theme"],
    revision: Literal["shorter", "deeper", "different_news"] | None = None,
    previous_post: dict | None = None,
) -> dict:
    inputs = (
        load_source_inputs_with_retries(post_type)
        if revision == "different_news"
        else load_source_inputs(post_type)
    )
    if revision == "different_news":
        inputs = select_alternative_signals(inputs, previous_post)
    if not inputs.get("signals"):
        raise FreshSourceDataUnavailable(
            f"No verified fresh signals for {inputs.get('date')}; draft generation stopped"
        )
    post = generate_post(inputs, post_type, revision, previous_post)
    allowed_source_urls = {
        str(signal.get("url"))
        for signal in inputs.get("signals", [])
        if signal.get("url")
    }
    if inputs.get("market_snapshot", {}).get("quotes"):
        allowed_source_urls.add("https://finance.yahoo.com/")
    fact_check = verify_post_grounding(post, inputs)
    fact_check["fresh_signals_checked"] = len(inputs.get("signals", []))
    fact_check["market_quotes_checked"] = len(
        inputs.get("market_snapshot", {}).get("quotes", [])
    )
    quality = check_post(post, allowed_source_urls, fact_check)
    temporary_id = uuid4().hex[:12]
    image_path = render_market_card(post, temporary_id)
    draft = create_draft(post, quality, image_path)
    final_image_path = image_path.with_name(f"{draft['id']}.png")
    image_path.replace(final_image_path)
    draft["image_path"] = str(final_image_path)
    from app.storage.drafts import save_draft

    save_draft(draft)
    return draft
