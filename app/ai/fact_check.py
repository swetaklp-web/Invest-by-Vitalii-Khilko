from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import settings


def verify_post_grounding(post: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    settings.require("openai_api_key")
    client = OpenAI(api_key=settings.openai_api_key)
    evidence = {
        "date": inputs.get("date"),
        "signals": inputs.get("signals", []),
        "market_snapshot": inputs.get("market_snapshot", {}),
    }
    response = client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты строгий факт-чекер инвестиционных публикаций. Проверяй каждое фактическое "
                    "утверждение, цифру, движение цены, причинно-следственную связь и новость только "
                    "по переданным evidence. Не используй знания из памяти. Аналитические выводы "
                    "разрешены только если они явно следуют из evidence. Верни JSON: "
                    '{"passed": boolean, "unsupported_claims": ["..."], "notes": ["..."]}. '
                    "Если утверждение нельзя подтвердить evidence, добавь его в unsupported_claims."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({"post": post, "evidence": evidence}, ensure_ascii=False),
            },
        ],
    )
    result = json.loads(response.choices[0].message.content or "{}")
    unsupported = [str(item) for item in result.get("unsupported_claims", [])]
    return {
        "passed": bool(result.get("passed")) and not unsupported,
        "unsupported_claims": unsupported,
        "notes": [str(item) for item in result.get("notes", [])],
    }
