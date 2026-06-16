from __future__ import annotations

import pytest

from atlas.core.config import load_config
from atlas.core.models import TradingMode
from atlas.runtime.engine import TradingEngine


def test_paper_requires_api_keys(monkeypatch, tmp_path):
    monkeypatch.delenv("BINANCE_DEMO_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_DEMO_API_SECRET", raising=False)

    config_path = tmp_path / "paper.yaml"
    config_path.write_text(
        """
mode: paper
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
    assert config.mode == TradingMode.PAPER

    with pytest.raises(RuntimeError, match="API keys missing"):
        TradingEngine(config)


def test_paper_accepts_api_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("BINANCE_DEMO_API_KEY", "test-key")
    monkeypatch.setenv("BINANCE_DEMO_API_SECRET", "test-secret")

    config_path = tmp_path / "paper.yaml"
    config_path.write_text(
        """
mode: paper
exchange:
  symbol: BTC/USDT
  timeframe: 4h
strategy:
  name: mm200_trend_v2
  params:
    warmup_bars: 205
database_url: postgresql://invalid:5432/nodb
""",
        encoding="utf-8",
    )
    config = load_config(config_path)
    engine = TradingEngine(config)
    assert engine.journal.using_file_fallback
