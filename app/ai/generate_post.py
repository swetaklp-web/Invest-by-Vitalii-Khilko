from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from openai import OpenAI

from app.config import ROOT_DIR, settings
from app.telegram.formatting import sanitize_telegram_html


PROMPTS_DIR = ROOT_DIR / "app" / "ai" / "prompts"


def _prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def generate_post(
    inputs: dict[str, Any],
    post_type: Literal["morning_brief", "evening_theme"],
    revision: Literal["shorter", "deeper", "different_news"] | None = None,
    previous_post: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings.require("openai_api_key")
    client = OpenAI(api_key=settings.openai_api_key)
    revision_instruction = {
        None: "",
        "shorter": "Переделай предыдущую версию короче, сохранив главную аналитику.",
        "deeper": "Переделай предыдущую версию глубже: усили цепочку влияния и риски.",
        "different_news": (
            "Создай пост на основе совершенно другой новости или рыночного сигнала. "
            "Не редактируй и не пересказывай предыдущий пост. Выбери другой главный сюжет, "
            "другой катализатор и по возможности другие тикеры. Если среди входных сигналов "
            "есть несколько тем, обязательно используй тему, не связанную с previous_post."
        ),
    }[revision]
    schema = {
        "post_type": post_type,
        "date": "YYYY-MM-DD",
        "title": (
            "Что важно перед открытием США"
            if post_type == "morning_brief"
            else "Главная тема дня на рынке"
        ),
        "tickers": ["NVDA"],
        "market_direction": "[Bullish] | [Bearish] | [Watch] | [Volatile]",
        "signal_strength": "high | medium | low",
        "horizon": "short | medium | long",
        "catalyst_type": "event | fundamental | flows | narrative | macro | technical | rumor",
        "sources": [{"name": "...", "url": "...", "summary": "..."}],
        "telegram_text": "...",
        "image_title": "Одно короткое законченное предложение до 92 символов.",
        "image_subtitle": "",
        "image_tickers": ["$NVDA"],
        "risk_flags": [],
    }
    user_payload = {
        "task": f"Создай пост типа {post_type}. {revision_instruction}",
        "current_date": datetime.now(ZoneInfo("Europe/Moscow")).date().isoformat(),
        "required_json_shape": schema,
        "input_signals": inputs,
        "previous_post": previous_post,
    }
    response = client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        temperature=0.4,
        messages=[
            {
                "role": "system",
                "content": "\n\n".join(
                    [
                        _prompt("system_invest_by_vitalii.md"),
                        _prompt("telegram_style.md"),
                        _prompt("compliance_rules.md"),
                        "Верни только валидный JSON. telegram_text не длиннее 1000 символов.",
                        (
                            "КРИТИЧЕСКОЕ ПРАВИЛО ШИРОКОГО РЫНКА: сначала сравни все свежие входные "
                            "сигналы по секторам, компаниям и классам активов. Выбирай тему по "
                            "рыночной значимости, а не по знакомости тикера. Не отдавай автоматический "
                            "приоритет AI, $NVDA, мегатехам или технологиям. Учитывай финансовый, "
                            "медицинский, энергетический, промышленный, потребительский, сырьевой, "
                            "коммунальный, real estate и small-cap сегменты, а также ставки, "
                            "облигации, доллар, нефть, золото, потоки, опционы и инсайдерскую активность. "
                            "Проверяй input_signals.source_quality.discovery_topics и covered_tickers. "
                            "Если покрытие узкое, не называй вывод картиной всего рынка."
                        ),
                        (
                            "КРИТИЧЕСКОЕ ПРАВИЛО АКТУАЛЬНОСТИ: используй только факты, которые явно "
                            "есть в input_signals.signals или input_signals.market_snapshot и относятся "
                            "к current_date. Не выдумывай новости, цифры, отчёты, сделки, слухи, "
                            "движения индексов или макроданные. Если свежих новостных сигналов мало, "
                            "сделай пост осторожным: опирайся на market_snapshot и прямо отмечай, что "
                            "сильный подтверждённый новостной катализатор не найден. Все sources должны "
                            "быть взяты только из входных сигналов. Для market_snapshot используй URL "
                            "https://finance.yahoo.com/ и название Yahoo Finance."
                        ),
                        (
                            "morning_brief обязан содержать: 3–5 драйверов, макро-блок "
                            "(ставки/доходности, доллар, нефть, золото), индексы США, 5–10 тикеров "
                            "и короткий вывод по настроению рынка. evening_theme обязан содержать один "
                            "сильный подтверждённый нарратив, почему рынок это обсуждает, связанные "
                            "компании/тикеры, потенциальный импульс, что подтвердит или сломает идею, "
                            "и краткий вывод для инвестора."
                        ),
                        (
                            "Для image_title верни ровно одно короткое законченное предложение "
                            "до 92 символов. Не используй фразы «на радаре» и "
                            "«альтернативный вариант обложки». image_subtitle всегда оставляй пустым."
                        ),
                    ]
                ),
            },
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    )
    post = json.loads(response.choices[0].message.content or "{}")
    post["telegram_text"] = sanitize_telegram_html(str(post.get("telegram_text", "")))
    return post
