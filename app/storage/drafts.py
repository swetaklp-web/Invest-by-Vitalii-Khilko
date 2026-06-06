import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import ROOT_DIR


DRAFTS_DIR = ROOT_DIR / "data" / "drafts"
PUBLISHED_DIR = ROOT_DIR / "data" / "published"


def create_draft(post: dict[str, Any], quality: dict[str, Any], image_path: Path) -> dict[str, Any]:
    draft = {
        "id": uuid4().hex[:12],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_review",
        "post": post,
        "quality": quality,
        "image_path": str(image_path),
        "telegram_message_id": None,
    }
    save_draft(draft)
    return draft


def save_draft(draft: dict[str, Any]) -> None:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    (DRAFTS_DIR / f"{draft['id']}.json").write_text(
        json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_draft(draft_id: str) -> dict[str, Any]:
    return json.loads((DRAFTS_DIR / f"{draft_id}.json").read_text(encoding="utf-8"))


def mark_published(draft: dict[str, Any]) -> None:
    draft["status"] = "published"
    draft["published_at"] = datetime.now(timezone.utc).isoformat()
    save_draft(draft)
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
    (PUBLISHED_DIR / f"{draft['id']}.json").write_text(
        json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8"
    )

