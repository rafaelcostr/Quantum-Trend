from __future__ import annotations

from datetime import datetime, timezone

from atlas.core.models import Candle, IndicatorSnapshot, Position, Side, SignalAction
from atlas.strategies.breakout_high20_v1 import build_breakout_high20_v1
from atlas.strategies.pullback_ema20_v1 import build_pullback_ema20_v1
from atlas.strategies.registry import list_strategies
from atlas.strategies.supertrend_mm200_v1 import build_supertrend_mm200_v1


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


def test_list_strategies_includes_new():
    names = list_strategies()
    assert "pullback_ema20_v1" in names
    assert "breakout_high20_v1" in names
    assert "supertrend_mm200_v1" in names


def test_pullback_ema20_enters_on_bounce():
    s = build_pullback_ema20_v1({})
    candle = _candle(open=101, high=102, low=99.5, close=101.5, volume=500)
    ind = IndicatorSnapshot(
        timestamp=candle.timestamp,
        ema20=100.0,
        ema200=95.0,
    )
    sig = s.evaluate(candle, ind, None)
    assert sig.action == SignalAction.ENTER_LONG


def test_breakout_high20_requires_volume():
    s = build_breakout_high20_v1({"volume_mult": 1.5})
    ind = IndicatorSnapshot(timestamp=datetime.now(timezone.utc), high_20=100.0, volume_sma20=1000.0, adx=20.0)
    low_vol = s.evaluate(_candle(close=101, volume=500), ind, None)
    assert low_vol.action == SignalAction.HOLD
    high_vol = s.evaluate(_candle(close=101, volume=2000), ind, None)
    assert high_vol.action == SignalAction.ENTER_LONG


def test_supertrend_mm200_enters_when_aligned():
    s = build_supertrend_mm200_v1({})
    candle = _candle(close=105, low=104, high=106)
    ind = IndicatorSnapshot(
        timestamp=candle.timestamp,
        ema200=100.0,
        supertrend=102.0,
        supertrend_dir=1.0,
        adx=25.0,
    )
    sig = s.evaluate(candle, ind, None)
    assert sig.action == SignalAction.ENTER_LONG


def test_supertrend_mm200_exits_on_flip():
    s = build_supertrend_mm200_v1({})
    candle = _candle(close=98, low=97)
    ind = IndicatorSnapshot(
        timestamp=candle.timestamp,
        ema200=100.0,
        supertrend=99.0,
        supertrend_dir=-1.0,
        adx=25.0,
    )
    pos = Position(
        symbol="BTC/USDT",
        side=Side.BUY,
        quantity=1.0,
        entry_price=105.0,
        entry_time=candle.timestamp,
    )
    sig = s.evaluate(candle, ind, pos)
    assert sig.action == SignalAction.EXIT_LONG
