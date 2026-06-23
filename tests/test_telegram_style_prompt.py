from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_telegram_style_has_financebks_emoji_rules() -> None:
    style = (ROOT / "app" / "ai" / "prompts" / "telegram_style.md").read_text(
        encoding="utf-8"
    )

    assert "Правила эмодзи по стилю канала @Financebks" in style
    assert "базовая норма: 0–1 эмодзи на пост" in style
    assert "до 4 стрелок `➡️`" in style
    assert "`📌` использовать только перед коротким итогом" in style
    assert "не декоративно" in style


def test_telegram_style_has_channel_post_rhythm() -> None:
    style = (ROOT / "app" / "ai" / "prompts" / "telegram_style.md").read_text(
        encoding="utf-8"
    )

    assert "Ритм постов по каналу @Financebks" in style
    assert "типичная длина 600–1000 символов" in style
    assert "первая строка сразу формулирует суть" in style
