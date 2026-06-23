from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_callbacks_preserve_subscription_link_when_replacing_images() -> None:
    source = (ROOT / "app" / "telegram" / "callbacks.py").read_text(encoding="utf-8")

    assert "ensure_subscription_link" in source
    assert source.count("ensure_subscription_link(") >= 2


def test_publisher_also_adds_subscription_link() -> None:
    source = (ROOT / "app" / "telegram" / "publisher.py").read_text(encoding="utf-8")

    assert "ensure_subscription_link" in source
    assert "caption=ensure_subscription_link" in source
