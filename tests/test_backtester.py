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


def test_simulated_broker_applies_min_notional_and_quantity_step(tmp_path):
    from atlas.brokers.simulated import SimulatedBroker
    from atlas.core.models import Candle, ExecutionConfig, Order, Side

    broker = SimulatedBroker(
        symbol="BTC/USDT",
        execution=ExecutionConfig(
            fee_rate=0.001,
            taker_fee_rate=0.002,
            min_order_notional=50,
            quantity_step=0.01,
        ),
        cash=10_000,
    )
    broker.set_candles([
        Candle(
            timestamp=pd.Timestamp("2024-01-01", tz="UTC").to_pydatetime(),
            open=100,
            high=101,
            low=99,
            close=100,
            volume=1000,
        )
    ])
    broker._cursor = 1  # noqa: SLF001

    small = broker.place_order(Order(symbol="BTC/USDT", side=Side.BUY, quantity=0.1))
    assert small.success is False

    ok = broker.place_order(Order(symbol="BTC/USDT", side=Side.BUY, quantity=0.637))
    assert ok.success is True
    assert ok.filled_quantity == pytest.approx(0.63)
    assert ok.fee == pytest.approx((ok.filled_price or 0) * 0.63 * 0.002)
