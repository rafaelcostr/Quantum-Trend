from __future__ import annotations

from datetime import datetime, timezone

import pytest

from atlas.core.models import Candle, IndicatorSnapshot, Position, Side, SignalAction
from atlas.strategies.bear.breakout_down_v1 import build_breakout_down_v1
from atlas.strategies.bear.pullback_short_v1 import build_pullback_short_v1
from atlas.strategies.bear.supertrend_bear_v1 import build_supertrend_bear_v1
from atlas.strategies.market_orchestrator import detect_execution_regime, gate_strategy_by_regime, validate_slot_market_mix
from atlas.strategies.metadata import get_market_type, is_bear_strategy
from atlas.strategies.registry import list_strategies


def _candle(**kwargs) -> Candle:
    defaults = {
        "timestamp": datetime(2024, 6, 1, tzinfo=timezone.utc),
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.5,
        "volume": 1000.0,
    }
    defaults.update(kwargs)
    return Candle(**defaults)


def test_bear_strategies_registered():
    names = list_strategies()
    assert "pullback_short_v1" in names
    assert "breakout_down_v1" in names
    assert "supertrend_bear_v1" in names
    assert is_bear_strategy("pullback_short_v1")
    assert get_market_type("pullback_ema20_v1") == "bull"
    assert get_market_type("pullback_short_v1") == "bear"


def test_slot_mix_validation():
    validate_slot_market_mix(["pullback_ema20_v1", "supertrend_mm200_v1"])
    with pytest.raises(ValueError, match="Bull e Bear"):
        validate_slot_market_mix(["pullback_ema20_v1", "pullback_short_v1"])


def test_slot_mix_allows_bull_btc_and_bear_eth():
    from atlas.runtime.operational_config import PaperSlot

    validate_slot_market_mix(
        [
            PaperSlot(strategy="pullback_ema20_v1", timeframe="4h", base="BTC", enabled=True),
            PaperSlot(strategy="pullback_short_v1", timeframe="4h", base="ETH", enabled=True),
        ]
    )


def test_regime_gate_blocks_bull_in_bear():
    candle = _candle(close=95)
    ind = IndicatorSnapshot(timestamp=candle.timestamp, ema200=100.0, adx=25.0)
    assert detect_execution_regime(candle, ind) == "bear"
    gate = gate_strategy_by_regime("pullback_ema20_v1", candle, ind)
    assert gate is not None
    assert gate.action == SignalAction.HOLD
    assert "regime gate" in gate.reason


def test_pullback_short_enters_on_rejection():
    s = build_pullback_short_v1({})
    candle = _candle(open=99.5, high=100.5, low=99.0, close=99.2, volume=800)
    ind = IndicatorSnapshot(
        timestamp=candle.timestamp,
        ema20=100.0,
        prev_ema20=100.5,
        ema200=105.0,
        adx=22.0,
        atr=2.0,
    )
    sig = s.evaluate(candle, ind, None)
    assert sig.action == SignalAction.ENTER_SHORT


def test_breakout_down_enters_on_low_break():
    s = build_breakout_down_v1({"volume_mult": 1.0})
    ind = IndicatorSnapshot(
        timestamp=datetime.now(timezone.utc),
        low_20=100.0,
        ema200=110.0,
        volume_sma20=500.0,
    )
    sig = s.evaluate(_candle(close=98, high=99, low=97, volume=800), ind, None)
    assert sig.action == SignalAction.ENTER_SHORT


def test_supertrend_bear_enters_when_aligned():
    s = build_supertrend_bear_v1({})
    candle = _candle(close=95, high=96, low=94, open=95.5)
    ind = IndicatorSnapshot(
        timestamp=candle.timestamp,
        ema20=96.0,
        ema200=100.0,
        supertrend=97.0,
        supertrend_dir=-1.0,
        adx=24.0,
        atr=2.0,
    )
    sig = s.evaluate(candle, ind, None)
    assert sig.action == SignalAction.ENTER_SHORT


def test_pullback_short_exits_on_stop():
    s = build_pullback_short_v1({})
    pos = Position(
        symbol="BTC/USDT",
        side=Side.SHORT,
        quantity=1.0,
        entry_price=100.0,
        entry_time=datetime.now(timezone.utc),
        stop_price=101.0,
        metadata={"position_kind": "short"},
    )
    sig = s.evaluate(_candle(high=101.5, close=101.2), IndicatorSnapshot(timestamp=datetime.now(timezone.utc)), pos)
    assert sig.action == SignalAction.EXIT_SHORT
