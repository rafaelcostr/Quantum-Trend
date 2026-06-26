from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.brokers.binance import fetch_ohlcv
from atlas.core.config import load_config
from atlas.core.env import project_root
from atlas.core.indicators import add_indicators_from_params
from atlas.core.models import AtlasConfig, BacktestMetrics, JournalEntry
from atlas.core.symbols import quote_from_symbol, report_name_stem
from atlas.intelligence.dashboard import compute_quick_atlas_score
from atlas.research.collector import load_or_download
from atlas.research.engine_backtest import run_backtest_engine
from atlas.research.reports import load_latest_report
from atlas.research.statistics import compute_buy_hold_return, compute_statistics, save_report
from atlas.strategies.mm200_trend_v2 import strategy_display_name
from atlas.strategies.registry import get_signal_fn


@dataclass
class QuickTrade:
    entry_time: str
    exit_time: str
    entry: float
    exit: float
    pnl: float
    pnl_pct: float


def run_backtest(config: AtlasConfig) -> tuple[BacktestMetrics, list[QuickTrade], pd.DataFrame]:
    """Backtest rapido para dashboard (500 candles)."""
    df = fetch_ohlcv(config.exchange.symbol, config.exchange.timeframe, limit=min(500, config.exchange.limit))
    df = add_indicators_from_params(df, config.strategy.params)
    signal_fn = get_signal_fn(config.strategy.name)
    capital = config.execution.initial_capital
    equity = capital
    in_position = False
    entry_price = 0.0
    entry_time = ""
    trades: list[QuickTrade] = []
    equity_rows: list[dict] = []
    fee = config.execution.fee_rate
    slip = config.execution.slippage_rate

    for i, (_, row) in enumerate(df.iterrows()):
        sig = signal_fn(row, in_position=in_position)
        ts = row.timestamp.isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"])
        if not in_position and sig.action.value == "enter_long":
            entry_price = float(row["close"]) * (1 + slip)
            entry_time = ts
            in_position = True
        elif in_position and sig.action.value == "exit_long":
            exit_price = float(row["close"]) * (1 - slip)
            qty = (equity * 0.95) / entry_price
            pnl = qty * (exit_price - entry_price) - qty * exit_price * fee
            equity += pnl
            trades.append(
                QuickTrade(entry_time=entry_time, exit_time=ts, entry=entry_price, exit=exit_price, pnl=pnl, pnl_pct=(exit_price / entry_price - 1) * 100)
            )
            in_position = False
        mark = float(row["close"]) if in_position else 0.0
        marked = equity
        if in_position:
            qty = (equity * 0.95) / entry_price
            marked = equity + qty * (mark - entry_price)
        equity_rows.append({"day": f"D{i + 1}", "equity": round(marked, 2)})

    metrics = _metrics_from_quick_trades(trades, capital, equity_rows)
    return metrics, trades, pd.DataFrame(equity_rows)


def _metrics_from_quick_trades(trades: list[QuickTrade], initial: float, equity_rows: list[dict]) -> BacktestMetrics:
    if not trades:
        return BacktestMetrics(
            total_return_pct=0, profit_factor=0, max_drawdown_pct=0, sharpe=0,
            win_rate_pct=0, trades=0, expectancy=0, atlas_score=0,
        )
    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.0001
    pf = gross_profit / gross_loss
    win_rate = len(wins) / len(trades) * 100
    expectancy = float(np.mean(pnls))
    equities = [r["equity"] for r in equity_rows]
    peak = equities[0]
    max_dd = 0.0
    for eq in equities:
        peak = max(peak, eq)
        max_dd = max(max_dd, (peak - eq) / peak if peak else 0)
    rets = pd.Series(pnls)
    sharpe = float(rets.mean() / rets.std() * np.sqrt(len(rets))) if rets.std() > 0 else 0
    total_return = (equities[-1] / initial - 1) * 100 if equities else 0
    score = compute_quick_atlas_score(
        drawdown_pct=max_dd * 100, profit_factor=pf, expectancy=expectancy,
        sharpe=sharpe, total_return_pct=total_return, trades=len(trades),
    )
    return BacktestMetrics(
        total_return_pct=round(total_return, 2), profit_factor=round(pf, 2),
        max_drawdown_pct=round(max_dd * 100, 2), sharpe=round(sharpe, 2),
        win_rate_pct=round(win_rate, 2), trades=len(trades), expectancy=round(expectancy, 2),
        atlas_score=score,
    )


def save_quick_report(config: AtlasConfig, metrics: BacktestMetrics, trades: list[QuickTrade], equity_df: pd.DataFrame | None = None) -> Path:
    out_dir = project_root() / "data" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{config.strategy.name}_report.json"
    payload = {
        "strategy": config.strategy.name,
        "symbol": config.exchange.symbol,
        "metrics": metrics.model_dump(),
        "trades": [t.__dict__ for t in trades[-50:]],
        "equity_curve": equity_df.to_dict(orient="records")[-120:] if equity_df is not None else [],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def trades_to_journal(trades: list[QuickTrade], strategy: str, symbol: str) -> list[JournalEntry]:
    asset = symbol if "/" in symbol else f"{symbol}/USDT"
    out: list[JournalEntry] = []
    for t in trades[-20:][::-1]:
        out.append(
            JournalEntry(
                date=t.exit_time[:16].replace("T", " "),
                asset=asset,
                entry=round(t.entry, 4),
                exit=round(t.exit, 4),
                pnl=round(t.pnl, 2),
                strategy=strategy_display_name(strategy),
            )
        )
    return out


def run_backtest_from_yaml(config_path: str) -> tuple[BacktestMetrics, Path]:
    from atlas.strategies.registry import build_strategy_from_config

    config = load_config(config_path)
    strategy = build_strategy_from_config(config.strategy.name, config.strategy.params)
    if getattr(strategy, "uses_multi_timeframe", False):
        from atlas.quantum.multi_timeframe import build_execution_dataset

        df = build_execution_dataset(config)
    else:
        df = load_or_download(config)
    warmup = int(config.strategy.params.get("warmup_bars", 205))
    buy_hold = compute_buy_hold_return(df, warmup, config.risk.initial_capital)
    result = run_backtest_engine(config, df)
    report = compute_statistics(result)
    quote = quote_from_symbol(config.exchange.symbol)
    base = config.exchange.symbol.split("/")[0]
    name = report_name_stem(config.strategy.name, config.exchange.timeframe, quote, base)
    out_dir = project_root() / "data" / "reports"
    path = save_report(
        result, report, out_dir, name=name, config=config,
        config_file=config_path, buy_hold_pct=buy_hold,
    )
    from atlas.intelligence.score import compute_atlas_score

    atlas = compute_atlas_score(
        max_drawdown_pct=report.max_drawdown_pct,
        profit_factor=min(report.profit_factor, 99.0),
        expectancy_pct=report.avg_trade_pct,
        sharpe=report.sharpe_ratio,
        net_profit_pct=report.net_profit_pct,
        total_trades=report.total_trades,
    )
    metrics = BacktestMetrics(
        total_return_pct=round(report.net_profit_pct * 100, 2),
        profit_factor=round(min(report.profit_factor, 99.0), 2),
        max_drawdown_pct=round(report.max_drawdown_pct * 100, 2),
        sharpe=round(report.sharpe_ratio or 0, 2),
        win_rate_pct=round(report.win_rate * 100, 2),
        trades=report.total_trades,
        expectancy=round(report.avg_trade_pct, 4),
        atlas_score=atlas,
    )
    return metrics, path


def run_walkforward_from_yaml(config_path: str, train_pct: float = 0.70) -> Path:
    from atlas.intelligence.research_store import save_walkforward
    from atlas.research.walkforward import run_walk_forward

    config = load_config(config_path)
    df = load_or_download(config)
    wf = run_walk_forward(config, df, train_pct=train_pct)
    return save_walkforward(wf, project_root() / "data" / "reports")


# re-export
__all__ = [
    "load_latest_report",
    "run_backtest",
    "run_backtest_from_yaml",
    "run_walkforward_from_yaml",
    "save_quick_report",
    "trades_to_journal",
]
