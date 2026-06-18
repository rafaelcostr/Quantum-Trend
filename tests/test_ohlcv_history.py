from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from atlas.brokers.binance import fetch_ohlcv_history, history_start_ms
from atlas.core.config import AtlasConfig
from atlas.research.collector import _cache_needs_refresh, load_or_download


def _fake_batches(symbol: str, timeframe: str, since: int | None = None, limit: int = 1000):
    base = since or 1_500_000_000_000
    rows = []
    for i in range(limit):
        ts = base + i * 3_600_000
        rows.append([ts, 100.0 + i, 101.0, 99.0, 100.5, 10.0])
    return rows


def test_fetch_ohlcv_history_paginates():
    calls: list[int | None] = []

    def side_effect(symbol, timeframe, since=None, limit=1000):
        calls.append(since)
        if len(calls) == 1:
            return _fake_batches(symbol, timeframe, since=since, limit=limit)
        if len(calls) == 2:
            return _fake_batches(symbol, timeframe, since=since, limit=500)
        return []

    mock_ex = MagicMock()
    mock_ex.fetch_ohlcv.side_effect = side_effect
    mock_ex.parse8601.return_value = 1_500_000_000_000

    with patch("atlas.brokers.binance._public_exchange", return_value=mock_ex):
        df = fetch_ohlcv_history("BTC/USDT", "1h", since_ms=1_500_000_000_000, max_batches=5)

    assert len(df) == 1500
    assert len(calls) == 2
    assert calls[1] == calls[0] + 999 * 3_600_000 + 1


def test_history_start_ms_years():
    mock_ex = MagicMock()
    mock_ex.parse8601.return_value = 1_500_000_000_000
    full = history_start_ms(mock_ex, "BTC/USDT", years=0)
    recent = history_start_ms(mock_ex, "BTC/USDT", years=2)
    assert recent > full


def test_cache_needs_refresh_detects_legacy_1000_rows():
    idx = pd.date_range("2024-01-01", periods=1000, freq="1D", tz="UTC")
    df = pd.DataFrame({"close": 1.0}, index=idx)
    cfg = AtlasConfig()
    cfg.data.years = 0
    cfg.exchange.timeframe = "1d"
    assert _cache_needs_refresh(df, cfg) is True


def test_load_or_download_refreshes_truncated_cache(tmp_path):
    cfg = AtlasConfig()
    cfg.data.cache_dir = str(tmp_path)
    cfg.data.years = 0
    cfg.exchange.timeframe = "1d"
    cache = tmp_path / "binance_BTCUSDT_1d.csv"
    idx = pd.date_range("2024-01-01", periods=1000, freq="1D", tz="UTC")
    pd.DataFrame({"open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}, index=idx).reset_index().rename(
        columns={"index": "timestamp"}
    ).to_csv(cache, index=False)

    full_idx = pd.date_range("2017-08-17", periods=1200, freq="1D", tz="UTC")
    fake = pd.DataFrame(
        {"timestamp": full_idx, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}
    ).set_index("timestamp")

    with patch("atlas.research.collector.fetch_ohlcv_history", return_value=fake.reset_index()):
        df = load_or_download(cfg, force=False)

    assert len(df) == 1200
    reloaded = pd.read_csv(cache, parse_dates=["timestamp"])
    assert len(reloaded) == 1200
