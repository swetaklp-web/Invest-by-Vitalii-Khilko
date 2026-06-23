from __future__ import annotations

import re
import time
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import uuid4

from app.ai.generate_post import generate_post
from app.ai.fact_check import verify_post_grounding
from app.ai.quality_check import check_post
from app.config import settings
from app.design.render_image import render_market_card
from app.editorial_policy import load_editorial_policy, score_signal
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


class FactCheckFailed(RuntimeError):
    def __init__(self, fact_check: dict) -> None:
        self.fact_check = fact_check
        unsupported = "; ".join(fact_check.get("unsupported_claims", []))
        message = unsupported or "Post did not pass fresh-source fact-check"
        super().__init__(message)


class DraftQualityFailed(RuntimeError):
    def __init__(self, quality: dict) -> None:
        self.quality = quality
        issues = "; ".join(quality.get("issues", []))
        super().__init__(issues or "Draft did not pass quality checks")


def create_news_image(post: dict, temporary_id: str, post_type: str) -> tuple[Path, str]:
    try:
        from app.design.generate_ai_image import generate_ai_news_image

        return generate_ai_news_image(post, temporary_id), "ai_generated"
    except Exception as error:
        write_log(
            {
                "post_type": post_type,
                "status": "image_generation_warning",
                "error": str(error),
                "fallback": "html_market_card",
            }
        )
        return render_market_card(post, temporary_id), "html_fallback"


def _allowed_source_urls(inputs: dict) -> set[str]:
    allowed = {
        str(signal.get("url"))
        for signal in inputs.get("signals", [])
        if signal.get("url")
    }
    if inputs.get("market_snapshot", {}).get("quotes"):
        allowed.add("https://finance.yahoo.com/")
    return allowed


def generate_grounded_post(
    inputs: dict,
    post_type: Literal["morning_brief", "evening_theme"],
    revision: Literal["shorter", "deeper", "different_news"] | None = None,
    previous_post: dict | None = None,
    attempts: int = 3,
) -> tuple[dict, dict]:
    grounding_feedback: dict | None = None
    last_fact_check: dict = {
        "passed": False,
        "unsupported_claims": [],
        "notes": ["Fact-check was not completed"],
    }
    for attempt in range(1, attempts + 1):
        post = generate_post(
            inputs,
            post_type,
            revision,
            previous_post,
            grounding_feedback=grounding_feedback,
        )
        fact_check = verify_post_grounding(post, inputs)
        fact_check["fresh_signals_checked"] = len(inputs.get("signals", []))
        fact_check["market_quotes_checked"] = len(
            inputs.get("market_snapshot", {}).get("quotes", [])
        )
        last_fact_check = fact_check
        if fact_check.get("passed"):
            return post, fact_check
        write_log(
            {
                "post_type": post_type,
                "status": "fact_check_retry",
                "attempt": attempt,
                "unsupported_claims": fact_check.get("unsupported_claims", []),
            }
        )
        grounding_feedback = {
            "attempt": attempt,
            "unsupported_claims": fact_check.get("unsupported_claims", []),
            "notes": fact_check.get("notes", []),
            "instruction": (
                "Remove unsupported claims and use only facts explicitly present "
                "in the provided fresh source evidence."
            ),
        }
    raise FactCheckFailed(last_fact_check)


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
    post, fact_check = generate_grounded_post(inputs, post_type, revision, previous_post)
    allowed_source_urls = _allowed_source_urls(inputs)
    quality = check_post(post, allowed_source_urls, fact_check)
    if not quality["passed"]:
        raise DraftQualityFailed(quality)
    temporary_id = uuid4().hex[:12]
    image_path, image_mode = create_news_image(post, temporary_id, post_type)
    draft = create_draft(post, quality, image_path)
    final_image_path = image_path.with_name(f"{draft['id']}.png")
    image_path.replace(final_image_path)
    draft["image_path"] = str(final_image_path)
    draft["image_mode"] = image_mode
    from app.storage.drafts import save_draft

    save_draft(draft)
    return draft


def discover_news_candidates(post_type: str, limit: int = 8) -> list[dict]:
    inputs = load_source_inputs_with_retries(post_type)
    policy = load_editorial_policy()
    seen_urls: set[str] = set()
    seen_topics: set[tuple[str, ...]] = set()
    candidates: list[dict] = []
    min_score = int(policy.get("min_score_for_auto_candidate", 0))
    scored_signals = []
    for signal in inputs.get("signals", []):
        signal = dict(signal)
        signal["editorial_score"] = score_signal(signal, policy)
        scored_signals.append(signal)
    signals = sorted(scored_signals, key=lambda item: item["editorial_score"], reverse=True)
    for signal in signals:
        if signal["editorial_score"] < min_score:
            continue
        url = str(signal.get("url") or "")
        topic = tuple(sorted(str(ticker) for ticker in signal.get("tickers", []) if ticker))
        if not url or url in seen_urls or (topic and topic in seen_topics):
            continue
        seen_urls.add(url)
        if topic:
            seen_topics.add(topic)
        candidates.append(signal)
        if len(candidates) >= limit:
            break
    return candidates


def recover_news_signal(selection_id: str, post_type: str) -> dict:
    for signal in discover_news_candidates(post_type, limit=30):
        identity = f"{post_type}:{signal.get('url', '')}:{signal.get('summary', '')}"
        if sha256(identity.encode("utf-8")).hexdigest()[:12] == selection_id:
            return signal
    raise FreshSourceDataUnavailable(
        "The selected news item is no longer present in today's verified sources"
    )


def build_draft_from_signal(
    post_type: Literal["morning_brief", "evening_theme"], signal: dict
) -> dict:
    inputs = load_source_inputs(post_type)
    inputs["signals"] = [signal]
    inputs["source_quality"]["selected_manually"] = True
    inputs["source_quality"]["fresh_signals_count"] = 1
    post, fact_check = generate_grounded_post(inputs, post_type)
    allowed_source_urls = {str(signal.get("url"))}
    quality = check_post(post, allowed_source_urls, fact_check)
    if not quality["passed"]:
        raise DraftQualityFailed(quality)
    temporary_id = uuid4().hex[:12]
    image_path, image_mode = create_news_image(post, temporary_id, post_type)
    draft = create_draft(post, quality, image_path)
    draft["image_mode"] = image_mode
    draft["selected_signal"] = signal
    from app.storage.drafts import save_draft

    save_draft(draft)
    return draft
