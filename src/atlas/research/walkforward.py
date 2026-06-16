from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from atlas.research.statistics import PerformanceReport, compute_statistics
from atlas.research.backtester import BacktestResult, run_backtest
from atlas.core.config import AtlasConfig
import pandas as pd


@dataclass
class WalkForwardResult:
    strategy: str
    train_pct: float
    split_index: int
    split_timestamp: str
    in_sample: PerformanceReport
    out_of_sample: PerformanceReport
    walk_forward_efficiency: float | None
    is_trades: int
    oos_trades: int


def _filter_oos_trades(result: BacktestResult, split_ts: pd.Timestamp) -> list:
    return [t for t in result.trades if t.entry_time >= split_ts.to_pydatetime()]


def _stats_from_trades_and_equity(
    trades,
    equity_curve,
    initial_capital: float,
    final_equity: float,
) -> PerformanceReport:
    partial = BacktestResult(
        trades=trades,
        equity_curve=equity_curve,
        initial_capital=initial_capital,
        final_equity=final_equity,
    )
    return compute_statistics(partial)


def run_walk_forward(
    config: AtlasConfig,
    df: pd.DataFrame,
    train_pct: float = 0.70,
) -> WalkForwardResult:
    if df.empty:
        raise ValueError("DataFrame vazio")

    warmup = int(config.strategy.params.get("warmup_bars", 205))
    n = len(df)
    split_idx = max(warmup + 10, int(n * train_pct))
    split_idx = min(split_idx, n - warmup - 10)
    split_ts = df.index[split_idx]

    # In-sample: backtest só no período de treino
    is_df = df.iloc[:split_idx].copy()
    is_result = run_backtest(config, is_df)

    # Out-of-sample: inclui warmup antes do split para indicadores
    oos_df = df.iloc[max(0, split_idx - warmup) :].copy()
    oos_full = run_backtest(config, oos_df)
    oos_trades = _filter_oos_trades(oos_full, split_ts)

    # Equity OOS: fatia da curva após split
    split_dt = split_ts.to_pydatetime()
    oos_equity = [(ts, eq) for ts, eq in oos_full.equity_curve if ts >= split_dt]
    if not oos_equity:
        oos_equity = [(split_dt, config.risk.initial_capital)]

    oos_initial = oos_equity[0][1]
    oos_final = oos_equity[-1][1]

    is_stats = compute_statistics(is_result)
    oos_stats = _stats_from_trades_and_equity(
        oos_trades, oos_equity, oos_initial, oos_final
    )

    wfe = None
    if is_stats.net_profit_pct > 0:
        wfe = float(oos_stats.net_profit_pct / is_stats.net_profit_pct)

    return WalkForwardResult(
        strategy=config.strategy.name,
        train_pct=train_pct,
        split_index=split_idx,
        split_timestamp=str(split_ts),
        in_sample=is_stats,
        out_of_sample=oos_stats,
        walk_forward_efficiency=wfe,
        is_trades=is_stats.total_trades,
        oos_trades=oos_stats.total_trades,
    )


def walk_forward_to_dict(wf: WalkForwardResult) -> dict[str, Any]:
    return {
        "strategy": wf.strategy,
        "train_pct": wf.train_pct,
        "split_index": wf.split_index,
        "split_timestamp": wf.split_timestamp,
        "walk_forward_efficiency": wf.walk_forward_efficiency,
        "in_sample": wf.in_sample.to_dict(),
        "out_of_sample": wf.out_of_sample.to_dict(),
        "is_trades": wf.is_trades,
        "oos_trades": wf.oos_trades,
    }
