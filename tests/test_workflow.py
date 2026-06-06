from app import workflow


class MissingOptionalSettings:
    def missing_optional_env_vars(self) -> list[str]:
        return ["X_API_KEY", "BARCHART_API_KEY"]


def test_missing_optional_keys_log_warning_and_use_manual_inputs(monkeypatch) -> None:
    events = []
    manual_inputs = {"signals": [{"source": "Manual input"}]}
    monkeypatch.setattr(workflow, "settings", MissingOptionalSettings())
    monkeypatch.setattr(workflow, "write_log", events.append)
    monkeypatch.setattr(workflow, "load_manual_inputs", lambda: manual_inputs)

    result = workflow.load_source_inputs("morning_brief")

    assert result == manual_inputs
    assert events[0]["status"] == "warning"
    assert events[0]["source_mode"] == "manual_inputs"
