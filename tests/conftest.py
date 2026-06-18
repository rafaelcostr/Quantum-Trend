from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def _build_equity_curve(initial: float = 10_000.0, points: int = 200) -> list[dict]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    curve: list[dict] = []
    equity = initial
    for i in range(points):
        # Smooth uptrend with mild oscillation and periodic pullbacks.
        equity += 12 + ((i % 9) - 4) * 3
        if i % 37 == 0 and i > 0:
            equity -= 180
        ts = start + timedelta(hours=4 * i)
        curve.append({"timestamp": ts.isoformat(), "equity": round(equity, 2)})
    return curve


def _build_trades(total: int = 84) -> list[dict]:
    base = datetime(2024, 1, 5, tzinfo=timezone.utc)
    trades: list[dict] = []
    for i in range(total):
        win = (i % 4) != 0  # 75% wins
        entry = base + timedelta(days=i * 3)
        exit_ = entry + timedelta(days=1)
        pnl = 72.0 if win else -30.0
        entry_price = 42_000 + i * 15
        exit_price = entry_price + (280 if win else -130)
        trades.append(
            {
                "entry_time": entry.isoformat(),
                "exit_time": exit_.isoformat(),
                "entry_price": float(entry_price),
                "exit_price": float(exit_price),
                "pnl": float(pnl),
                "pnl_pct": float(0.013 if win else -0.006),
                "fees": 1.2,
                "strategy": "mm200_trend_v1",
                "metadata": {"regime": "trend_up" if win else "pullback"},
            }
        )
    return trades


def _build_report_payload() -> dict:
    trades = _build_trades(84)
    equity_curve = _build_equity_curve(points=200)
    return {
        "metadata": {
            "strategy": "mm200_trend_v1",
            "strategy_version": "1.0.0",
            "strategy_type": "Trend Following",
            "market": "BTC/USDT",
            "timeframe": "4h",
            "config_file": "config/backtest_v2_2.yaml",
            "mode": "backtest",
            "risk_model": "risk_based",
            "position_size": "1% per trade",
            "fee_rate": 0.001,
            "slippage_rate": 0.0005,
            "initial_capital": 10000,
            "legacy_report": True,
        },
        "statistics": {
            "net_profit": 3500.0,
            "net_profit_pct": 0.35,
            "total_trades": 84,
            "win_rate": 0.75,
            "profit_factor": 1.8,
            "max_drawdown_pct": 0.14,
            "best_trade_pct": 0.026,
            "worst_trade_pct": -0.012,
            "avg_trade_pct": 0.0042,
            "expectancy_pct": 0.0042,
            "sharpe_ratio": 1.45,
            "sortino_ratio": 2.1,
            "recovery_factor": 2.5,
            "calmar_ratio": 1.4,
        },
        "trades": trades,
        "equity_curve": equity_curve,
    }


def _build_walkforward_payload() -> dict:
    return {
        "strategy": "mm200_trend_v1",
        "split_timestamp": "2025-01-01T00:00:00+00:00",
        "in_sample": {
            "net_profit_pct": 0.48,
            "profit_factor": 1.9,
            "sharpe_ratio": 1.5,
            "total_trades": 60,
        },
        "out_of_sample": {
            "net_profit_pct": 0.16,
            "profit_factor": 1.42,
            "sharpe_ratio": 1.08,
            "total_trades": 24,
        },
        "oos_return": 0.16,
        "oos_trades": 24,
        "walk_forward_efficiency": 0.33,
    }


@pytest.fixture(scope="session", autouse=True)
def ensure_intelligence_reports() -> None:
    root = Path(__file__).resolve().parents[1]
    reports_dir = root / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_path = reports_dir / "mm200_trend_v1_report.json"
    report_path.write_text(json.dumps(_build_report_payload(), indent=2), encoding="utf-8")

    walkforward_path = reports_dir / "mm200_trend_v1_walkforward.json"
    walkforward_path.write_text(json.dumps(_build_walkforward_payload(), indent=2), encoding="utf-8")
