from app.storage.logs import _redact


def test_redacts_secrets(monkeypatch) -> None:
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "secret-token-value")
    result = _redact({"error": "request failed for secret-token-value"})
    assert result["error"] == "request failed for [REDACTED]"
