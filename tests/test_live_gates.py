from __future__ import annotations

import pytest

from atlas.core.config import load_config
from atlas.core.models import TradingMode
from atlas.runtime.engine import TradingEngine
from atlas.runtime.live_gates import evaluate_live_gates


def test_live_requires_api_keys(monkeypatch, tmp_path):
    monkeypatch.delenv("BINANCE_LIVE_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_LIVE_API_SECRET", raising=False)

    config_path = tmp_path / "live.yaml"
    config_path.write_text(
        """
mode: live
exchange:
 symbol: BTC/USDT
 timeframe: 4h
strategy:
 name: mm200_trend_v2
 params:
  warmup_bars: 205
""",
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert config.mode == TradingMode.LIVE

    with pytest.raises(RuntimeError, match="API keys missing"):
        TradingEngine(config)


def test_live_gates_blocked_without_opt_in(monkeypatch):
    monkeypatch.setenv("ATLAS_ALLOW_LIVE", "0")
    monkeypatch.setenv("ATLAS_LIVE_MIN_PAPER_DAYS", "0")
    gates = evaluate_live_gates()
    assert gates["eligible"] is False
    assert any("Opt-in" in c["label"] for c in gates["checks"])


def test_live_gates_structure(monkeypatch):
    monkeypatch.setenv("ATLAS_ALLOW_LIVE", "1")
    monkeypatch.setenv("ATLAS_LIVE_MIN_PAPER_DAYS", "0")
    monkeypatch.setenv("BINANCE_LIVE_API_KEY", "k")
    monkeypatch.setenv("BINANCE_LIVE_API_SECRET", "s")
    gates = evaluate_live_gates()
    assert "checks" in gates
    assert "eligible" in gates
    assert gates["checks_total"] >= 5
