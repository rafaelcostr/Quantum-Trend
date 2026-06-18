from pathlib import Path
from unittest.mock import MagicMock, patch

from atlas.core.config import load_config
from atlas.dashboard.actions import run_backtest_dashboard

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_run_backtest_calls_engine_not_recursive():
    """Dashboard run_backtest must call research engine, not itself."""
    config_rel = "config/backtest.yaml"
    config = load_config(PROJECT_ROOT / config_rel)

    fake_result = MagicMock()
    fake_report = MagicMock(
        net_profit=100.0,
        net_profit_pct=0.01,
        total_trades=5,
        win_rate=0.6,
        profit_factor=1.5,
        max_drawdown_pct=0.1,
        sharpe_ratio=1.1,
    )

    with (
        patch("atlas.dashboard.actions.load_or_download", return_value=MagicMock(empty=False, __len__=lambda s: 100)),
        patch("atlas.dashboard.actions.run_backtest_engine", return_value=fake_result) as engine,
        patch("atlas.dashboard.actions.compute_statistics", return_value=fake_report),
        patch("atlas.dashboard.actions.compute_buy_hold_return", return_value=0.05),
        patch("atlas.dashboard.actions.save_report", return_value=Path("data/reports/x.json")),
    ):
        res = run_backtest_dashboard(PROJECT_ROOT, config_rel, timeframe="1d", quote="USDC")

    assert res["ok"] is True
    assert res["timeframe"] == "1d"
    assert res["symbol"] == "BTC/USDC"
    engine.assert_called_once()
    called_config = engine.call_args[0][0]
    assert called_config.exchange.timeframe == "1d"
    assert called_config.exchange.symbol == "BTC/USDC"
