from app.sources import barchart, oninvest, telegram_reader


class EmptySettings:
    barchart_api_key = ""
    oninvest_api_key = ""
    telegram_api_id = ""
    telegram_api_hash = ""
    telegram_session_string = ""


def test_optional_source_adapters_return_empty_without_credentials(monkeypatch) -> None:
    monkeypatch.setattr(barchart, "settings", EmptySettings())
    monkeypatch.setattr(oninvest, "settings", EmptySettings())
    monkeypatch.setattr(telegram_reader, "settings", EmptySettings())

    assert barchart.fetch_barchart_signals() == []
    assert oninvest.fetch_oninvest_signals() == []
    assert telegram_reader.fetch_telegram_signals() == []
