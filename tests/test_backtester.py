import pandas as pd
import pytest

from atlas.core.config import load_config
from atlas.research.engine_backtest import run_backtest_engine


@pytest.fixture
def sample_ohlcv():
    n = 400
    idx = pd.date_range("2023-01-01", periods=n, freq="4h", tz="UTC")
    close = [40_000.0 + i for i in range(n)]
    return pd.DataFrame(
        {
            "open": [c - 10 for c in close],
            "high": [c + 50 for c in close],
            "low": [c - 50 for c in close],
            "close": close,
            "volume": [1000.0] * n,
        },
        index=idx,
    )


def test_backtest_runs(sample_ohlcv, tmp_path):
    config_path = tmp_path / "backtest.yaml"
    config_path.write_text(
        """
mode: backtest
exchange:
 symbol: BTC/USDT
 timeframe: 4h
strategy:
 name: range_hunter_v1
 params:
  bb_period: 20
  bb_std: 2.0
  rsi_period: 14
  adx_period: 14
risk:
 initial_capital: 10000
execution:
 fee_rate: 0.001
 slippage_rate: 0.0005
""",
        encoding="utf-8",
    )
    config = load_config(config_path)
    result = run_backtest_engine(config, sample_ohlcv)
    assert result.final_equity > 0
    assert isinstance(result.trades, list)
