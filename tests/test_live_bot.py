from __future__ import annotations

import pytest

from atlas.core.models import TradingMode
from atlas.runtime.state import BotState


def test_start_live_requires_gates(monkeypatch):
    monkeypatch.setenv("ATLAS_ALLOW_LIVE", "0")
    state = BotState()
    with pytest.raises(RuntimeError, match="Gates live"):
        state.start_live()


def test_start_paper_sets_mode(monkeypatch):
    monkeypatch.setenv("BINANCE_DEMO_API_KEY", "demo-key")
    monkeypatch.setenv("BINANCE_DEMO_API_SECRET", "demo-secret")
    state = BotState()
    try:
        state.start_paper()
        snap = state.snapshot()
        assert snap["mode"] == TradingMode.PAPER.value
        assert snap["running"] is True
    finally:
        state.stop()
