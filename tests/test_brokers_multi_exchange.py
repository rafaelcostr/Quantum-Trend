from __future__ import annotations

import pytest

from atlas.brokers.base import BrokerVenue, ExchangeId, MarketType, market_spec
from atlas.brokers.factory import build_broker, broker_venue_for_config, requires_exchange_credentials
from atlas.brokers.simulated import SimulatedBroker
from atlas.core.config import load_config


def _config(tmp_path, body: str):
    path = tmp_path / "cfg.yaml"
    path.write_text(body, encoding="utf-8")
    return load_config(path)


def test_market_spec_normalizes_symbol_and_market_metadata():
    spec = market_spec(
        "BTCUSDT",
        exchange_id="binance",
        market_type="futures",
        venue="demo_exchange",
        min_notional=5,
        quantity_step=0.001,
    )
    assert spec.canonical_symbol == "BTC/USDT"
    assert spec.compact_symbol == "BTCUSDT"
    assert spec.market_type == MarketType.FUTURES
    assert spec.venue == BrokerVenue.DEMO_EXCHANGE
    assert spec.min_notional == 5
    assert spec.quantity_step == 0.001


def test_factory_builds_local_paper_without_exchange_credentials(tmp_path):
    cfg = _config(
        tmp_path,
        """
mode: paper
exchange:
  id: simulated
  symbol: BTCUSDT
  timeframe: 4h
  venue: paper_local
  market_type: spot
strategy:
  name: mm200_trend_v2
execution:
  min_order_notional: 10
  quantity_step: 0.001
risk:
  initial_capital: 1234
""",
    )
    assert broker_venue_for_config(cfg) == BrokerVenue.PAPER_LOCAL
    assert requires_exchange_credentials(cfg) is False
    broker = build_broker(cfg)
    assert isinstance(broker, SimulatedBroker)
    assert broker.symbol == "BTC/USDT"
    assert broker.get_balance() == 1234
    assert broker.market_spec().min_notional == 10
    assert broker.market_spec().quantity_step == 0.001


def test_factory_rejects_future_exchange_with_clear_message(tmp_path):
    cfg = _config(
        tmp_path,
        """
mode: paper
exchange:
  id: bybit
  symbol: BTC/USDT
  timeframe: 4h
  venue: demo_exchange
strategy:
  name: mm200_trend_v2
""",
    )
    with pytest.raises(NotImplementedError, match="bybit"):
        build_broker(cfg)


def test_factory_marks_binance_demo_as_credentials_required(tmp_path):
    cfg = _config(
        tmp_path,
        """
mode: paper
exchange:
  id: binance
  symbol: BTC/USDT
  timeframe: 4h
  venue: demo_exchange
strategy:
  name: mm200_trend_v2
""",
    )
    assert requires_exchange_credentials(cfg) is True
    assert broker_venue_for_config(cfg) == BrokerVenue.DEMO_EXCHANGE
    assert ExchangeId.BINANCE.value == "binance"
