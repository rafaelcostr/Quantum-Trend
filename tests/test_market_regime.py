from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from atlas.core.models import Candle, IndicatorSnapshot
from atlas.services.market_regime import (
    explain_execution_regime,
    get_market_regime_snapshot,
)


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


def test_explain_bull_regime():
    candle = _candle(close=105.0)
    ind = IndicatorSnapshot(timestamp=candle.timestamp, ema200=100.0, adx=25.0)
    text = explain_execution_regime(candle, ind)
    assert "acima" in text
    assert "ADX" in text


def test_explain_range_low_adx():
    candle = _candle(close=100.0)
    ind = IndicatorSnapshot(timestamp=candle.timestamp, ema200=100.0, adx=12.0)
    text = explain_execution_regime(candle, ind)
    assert "lateral" in text.lower()


def test_snapshot_from_candles():
    candles = []
    price = 90_000.0
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for i in range(250):
        candles.append(
            Candle(
                timestamp=base + timedelta(hours=i),
                open=price,
                high=price + 100,
                low=price - 100,
                close=price - 50 if i % 3 == 0 else price + 20,
                volume=1000.0,
            )
        )

    with patch("atlas.services.market_regime.fetch_public_candles", return_value=candles):
        with patch("atlas.services.market_regime.load_paper_slots", return_value=[]):
            snap = get_market_regime_snapshot()

    assert snap["available"] is True
    assert snap["market_type"] in {"bull", "bear", "range"}
    assert snap["label"] in {"Alta", "Baixa", "Lateral"}
    assert snap["strategies_route"].startswith("/estrategias-")


def test_snapshot_handles_fetch_error():
    with patch("atlas.services.market_regime.fetch_public_candles", side_effect=RuntimeError("network")):
        snap = get_market_regime_snapshot()

    assert snap["available"] is False
    assert snap["error"]
