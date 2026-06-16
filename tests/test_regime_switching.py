from datetime import datetime, timezone

from atlas.core.models import Candle, IndicatorSnapshot, SignalAction
from atlas.strategies.regime_switching_v1 import RegimeSwitchingV1


def test_range_regime_entry():
    strategy = RegimeSwitchingV1()
    signal = strategy.evaluate(
        Candle(
            timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
            open=94, high=96, low=93, close=95, volume=100,
        ),
        IndicatorSnapshot(
            timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
            bb_lower=100,
            bb_mid=110,
            rsi=30,
            adx=15,
            support=94,
            mm200=80,
        ),
        None,
    )
    assert signal.action == SignalAction.ENTER_LONG
    assert signal.metadata.get("regime") == "range"


def test_trend_regime_pullback_entry():
    strategy = RegimeSwitchingV1(enable_trend_entries=True)
    signal = strategy.evaluate(
        Candle(
            timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
            open=49900, high=50300, low=49900, close=50100, volume=100,
        ),
        IndicatorSnapshot(
            timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
            bb_mid=50000,
            rsi=50,
            adx=30,
            mm20=50000,
            mm200=48000,
            atr=500,
        ),
        None,
    )
    assert signal.action == SignalAction.ENTER_LONG
    assert signal.metadata.get("regime") == "trend_up"


def test_uncertain_regime_no_entry():
    strategy = RegimeSwitchingV1()
    signal = strategy.evaluate(
        Candle(
            timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
            open=100, high=101, low=99, close=100, volume=100,
        ),
        IndicatorSnapshot(
            timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
            adx=22,
            mm200=90,
        ),
        None,
    )
    assert signal.action == SignalAction.HOLD
