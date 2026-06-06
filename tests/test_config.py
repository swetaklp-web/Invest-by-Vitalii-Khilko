from app.config import OPTIONAL_ENV_VARS, Settings


def test_missing_optional_keys_do_not_raise(monkeypatch) -> None:
    for name in OPTIONAL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    settings = Settings()

    assert settings.missing_optional_env_vars() == list(OPTIONAL_ENV_VARS)


def test_required_keys_are_checked_separately(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings()

    try:
        settings.require("openai_api_key")
    except RuntimeError as error:
        assert "OPENAI_API_KEY" in str(error)
    else:
        raise AssertionError("Missing required key must raise")


def test_require_mvp_checks_all_required_values(monkeypatch) -> None:
    for name in ("OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_REVIEW_CHAT_ID", "TELEGRAM_CHANNEL_ID"):
        monkeypatch.delenv(name, raising=False)

    try:
        Settings().require_mvp()
    except RuntimeError as error:
        assert "TELEGRAM_REVIEW_CHAT_ID" in str(error)
        assert "TELEGRAM_CHANNEL_ID" in str(error)
    else:
        raise AssertionError("Missing MVP keys must raise")
