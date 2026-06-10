import json
from hashlib import sha256
from datetime import datetime, timezone

from app.config import ROOT_DIR


SELECTIONS_DIR = ROOT_DIR / "data" / "drafts" / "news_selections"


def save_news_selection(signal: dict, post_type: str) -> str:
    identity = f"{post_type}:{signal.get('url', '')}:{signal.get('summary', '')}"
    selection_id = sha256(identity.encode("utf-8")).hexdigest()[:12]
    payload = {
        "id": selection_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "post_type": post_type,
        "signal": signal,
    }
    SELECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    (SELECTIONS_DIR / f"{selection_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return selection_id


def load_news_selection(selection_id: str) -> dict:
    path = SELECTIONS_DIR / f"{selection_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"News selection {selection_id} is no longer available")
    return json.loads(path.read_text(encoding="utf-8"))
