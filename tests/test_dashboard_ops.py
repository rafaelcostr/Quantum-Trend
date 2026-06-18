from pathlib import Path

import pytest

from atlas.dashboard.strategy_config import build_operational_config, discover_strategy_configs, list_strategy_names
from atlas.dashboard.trades_history_ui import trades_to_dataframe

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_build_operational_config_usdc_1d():
    config = build_operational_config(
        PROJECT_ROOT,
        strategy_name="mm200_trend_v2",
        quote_asset="USDC",
        timeframe="1d",
    )
    assert config.exchange.symbol == "BTC/USDC"
    assert config.exchange.timeframe == "1d"
    assert config.strategy.name == "mm200_trend_v2"


def test_discover_strategy_configs():
    mapping = discover_strategy_configs(PROJECT_ROOT)
    assert "range_hunter_v1" in mapping
    assert len(mapping) >= 5


def test_list_strategy_names():
    names = list_strategy_names(PROJECT_ROOT)
    assert "mm200_trend_v2" in names


def test_trades_to_dataframe_empty():
    assert trades_to_dataframe([]).empty


def test_trades_to_dataframe_cum_flow():
    df = trades_to_dataframe(
        [
            {"timestamp": 1_700_000_000_000, "side": "buy", "price": 100, "amount": 0.1, "cost": 10, "fee": 0.01},
            {"timestamp": 1_700_100_000_000, "side": "sell", "price": 110, "amount": 0.1, "cost": 11, "fee": 0.01},
        ]
    )
    assert len(df) == 2
    assert df["cum_flow"].iloc[-1] == pytest.approx(-1.0)
