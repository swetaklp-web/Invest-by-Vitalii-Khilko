import pytest

from app import workflow


def test_build_draft_stops_when_no_fresh_signals(monkeypatch) -> None:
    monkeypatch.setattr(
        workflow,
        "load_source_inputs",
        lambda _: {"date": "2026-06-08", "signals": [], "market_snapshot": {"quotes": []}},
    )

    with pytest.raises(workflow.FreshSourceDataUnavailable):
        workflow.build_draft("morning_brief")
