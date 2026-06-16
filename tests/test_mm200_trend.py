from datetime import datetime, timezone

from atlas.core.models import Candle, IndicatorSnapshot, Position, Side, SignalAction
from atlas.strategies.mm200_trend_v1 import MM200TrendV1
from atlas.strategies.mm200_trend_v2 import MM200TrendV2


def test_enter_above_mm200():
    strategy = MM200TrendV1()
    signal = strategy.evaluate(
        Candle(
            timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
            open=51000, high=51500, low=50500, close=51200, volume=100,
        ),
        IndicatorSnapshot(timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc), mm200=50000),
        None,
    )
    assert signal.action == SignalAction.ENTER_LONG


def test_exit_below_mm200():
    strategy = MM200TrendV1()
    signal = strategy.evaluate(
        Candle(
            timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
            open=49000, high=49500, low=48500, close=48800, volume=100,
        ),
        IndicatorSnapshot(timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc), mm200=50000),
        Position(
            symbol="BTC/USDT",
            side=Side.BUY,
            quantity=0.1,
            entry_price=51000,
            entry_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
        ),
    )
    assert signal.action == SignalAction.EXIT_LONG


def test_flat_below_mm200():
    strategy = MM200TrendV1()
    signal = strategy.evaluate(
        Candle(
            timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
            open=48000, high=48500, low=47500, close=48200, volume=100,
        ),
        IndicatorSnapshot(timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc), mm200=50000),
        None,
    )
    assert signal.action == SignalAction.HOLD


def _position() -> Position:
    return Position(
        symbol="BTC/USDT",
        side=Side.BUY,
        quantity=0.1,
        entry_price=51000,
        entry_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
    )


def test_v2_exit_on_bearish_cross_only():
    strategy = MM200TrendV2()
    ts = datetime(2024, 6, 1, tzinfo=timezone.utc)
    signal = strategy.evaluate(
        Candle(timestamp=ts, open=49000, high=49500, low=48500, close=48800, volume=100),
        IndicatorSnapshot(timestamp=ts, mm200=50000, prev_close=51000),
        _position(),
    )
    assert signal.action == SignalAction.EXIT_LONG


def test_v2_hold_when_below_mm200_without_cross():
    strategy = MM200TrendV2()
    ts = datetime(2024, 6, 1, tzinfo=timezone.utc)
    signal = strategy.evaluate(
        Candle(timestamp=ts, open=48000, high=48500, low=47500, close=48200, volume=100),
        IndicatorSnapshot(timestamp=ts, mm200=50000, prev_close=48000),
        _position(),
    )
    assert signal.action == SignalAction.HOLD


def test_v2_no_entry_without_bullish_cross():
    strategy = MM200TrendV2()
    ts = datetime(2024, 6, 1, tzinfo=timezone.utc)
    signal = strategy.evaluate(
        Candle(timestamp=ts, open=51000, high=51500, low=50500, close=51200, volume=100),
        IndicatorSnapshot(timestamp=ts, mm200=50000, prev_close=51000),
        None,
    )
    assert signal.action == SignalAction.HOLD


def test_v2_enter_on_bullish_cross():
    strategy = MM200TrendV2()
    ts = datetime(2024, 6, 1, tzinfo=timezone.utc)
    signal = strategy.evaluate(
        Candle(timestamp=ts, open=49800, high=50500, low=49500, close=50200, volume=100),
        IndicatorSnapshot(timestamp=ts, mm200=50000, prev_close=49800),
        None,
    )
    assert signal.action == SignalAction.ENTER_LONG
