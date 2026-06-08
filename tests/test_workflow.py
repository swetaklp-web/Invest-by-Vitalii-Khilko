from app import workflow


class MissingOptionalSettings:
    def missing_optional_env_vars(self) -> list[str]:
        return ["X_API_KEY", "BARCHART_API_KEY"]


def test_missing_optional_keys_log_warning_and_use_manual_inputs(monkeypatch) -> None:
    events = []
    manual_inputs = {"signals": [{"source": "Manual input", "date": "2026-06-06"}]}
    monkeypatch.setattr(workflow, "settings", MissingOptionalSettings())
    monkeypatch.setattr(workflow, "write_log", events.append)
    monkeypatch.setattr(workflow, "load_manual_inputs", lambda: manual_inputs)
    monkeypatch.setattr(workflow, "today_moscow", lambda: "2026-06-08")
    monkeypatch.setattr(workflow, "fetch_yahoo_market_snapshot", lambda: {"date": "2026-06-08", "quotes": []})
    monkeypatch.setattr(workflow, "fetch_x_signals", lambda: [])
    monkeypatch.setattr(workflow, "fetch_yahoo_signals", lambda: [])
    monkeypatch.setattr(workflow, "fetch_barchart_signals", lambda: [])
    monkeypatch.setattr(workflow, "fetch_telegram_signals", lambda: [])
    monkeypatch.setattr(workflow, "fetch_oninvest_signals", lambda: [])

    result = workflow.load_source_inputs("morning_brief")

    assert result["signals"] == []
    assert result["source_mode"] == "market_snapshot_only"
    assert result["source_quality"]["stale_manual_signals_dropped"] == 1
    assert any(event["status"] == "warning" for event in events)
