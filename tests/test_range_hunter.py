from datetime import datetime, timezone

from atlas.core.models import Candle, IndicatorSnapshot, SignalAction
from atlas.strategies.range_hunter_v1 import RangeHunterV1


def _candle(close: float, low: float | None = None, high: float | None = None) -> Candle:
    return Candle(
        timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
        open=close,
        high=high or close + 10,
        low=low or close - 10,
        close=close,
        volume=100.0,
    )


def test_no_entry_when_adx_high():
    strategy = RangeHunterV1()
    signal = strategy.evaluate(
        _candle(90),
        IndicatorSnapshot(
            timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
            bb_lower=100,
            bb_mid=110,
            rsi=30,
            adx=30,
        ),
        None,
    )
    assert signal.action == SignalAction.HOLD


def test_entry_when_range_and_oversold():
    strategy = RangeHunterV1()
    signal = strategy.evaluate(
        _candle(95),
        IndicatorSnapshot(
            timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
            bb_lower=100,
            bb_mid=110,
            rsi=30,
            adx=18,
            support=94,
        ),
        None,
    )
    assert signal.action == SignalAction.ENTER_LONG
    assert signal.stop_price is not None
    assert signal.target_price == 110
