from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from atlas.core.config import AtlasConfig
from atlas.core.models import Trade
from atlas.research.engine_backtest import BacktestResult, run_backtest_engine
from atlas.research.statistics import PerformanceReport, compute_statistics


@dataclass
class WalkForwardWindow:
    index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train: PerformanceReport
    test: PerformanceReport
    test_trades: int
    efficiency: float | None


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
    holdout: PerformanceReport | None = None
    holdout_trades: int = 0
    holdout_split_timestamp: str | None = None
    rolling_windows: list[WalkForwardWindow] = field(default_factory=list)
    monte_carlo: dict[str, Any] = field(default_factory=dict)
    robustness: dict[str, Any] = field(default_factory=dict)
    promotion_checklist: list[dict[str, Any]] = field(default_factory=list)


def _filter_oos_trades(result: BacktestResult, split_ts: pd.Timestamp) -> list:
    return [t for t in result.trades if t.entry_time >= split_ts.to_pydatetime()]


def _stats_from_trades_and_equity(trades, equity_curve, initial_capital: float, final_equity: float) -> PerformanceReport:
    partial = BacktestResult(
        trades=trades,
        equity_curve=equity_curve,
        initial_capital=initial_capital,
        final_equity=final_equity,
    )
    return compute_statistics(partial)


def _slice_result_stats(config: AtlasConfig, df: pd.DataFrame, *, start_idx: int, end_idx: int, warmup: int) -> PerformanceReport:
    window = df.iloc[max(0, start_idx - warmup) : end_idx].copy()
    if len(window) <= warmup + 2:
        empty = BacktestResult(
            trades=[],
            equity_curve=[],
            initial_capital=config.risk.initial_capital,
            final_equity=config.risk.initial_capital,
        )
        return compute_statistics(empty)
    result = run_backtest_engine(config, window)
    start_ts = df.index[start_idx].to_pydatetime()
    trades = [t for t in result.trades if t.entry_time >= start_ts]
    equity = [(ts, eq) for ts, eq in result.equity_curve if ts >= start_ts]
    if not equity:
        equity = [(start_ts, config.risk.initial_capital)]
    return _stats_from_trades_and_equity(trades, equity, equity[0][1], equity[-1][1])


def _run_rolling_windows(
    config: AtlasConfig,
    df: pd.DataFrame,
    *,
    warmup: int,
    train_window_pct: float = 0.50,
    test_window_pct: float = 0.15,
    max_windows: int = 6,
) -> list[WalkForwardWindow]:
    n = len(df)
    train_len = max(warmup + 20, int(n * train_window_pct))
    test_len = max(20, int(n * test_window_pct))
    step = test_len
    windows: list[WalkForwardWindow] = []
    start = 0
    idx = 1
    while start + train_len + test_len <= n and len(windows) < max_windows:
        train_start = start
        train_end = start + train_len
        test_start = train_end
        test_end = train_end + test_len
        train_stats = _slice_result_stats(config, df, start_idx=train_start, end_idx=train_end, warmup=warmup)
        test_stats = _slice_result_stats(config, df, start_idx=test_start, end_idx=test_end, warmup=warmup)
        efficiency = (
            float(test_stats.net_profit_pct / train_stats.net_profit_pct)
            if train_stats.net_profit_pct > 0
            else None
        )
        windows.append(
            WalkForwardWindow(
                index=idx,
                train_start=str(df.index[train_start]),
                train_end=str(df.index[train_end - 1]),
                test_start=str(df.index[test_start]),
                test_end=str(df.index[test_end - 1]),
                train=train_stats,
                test=test_stats,
                test_trades=test_stats.total_trades,
                efficiency=efficiency,
            )
        )
        idx += 1
        start += step
    return windows


def _max_drawdown_from_equity(equity: list[float]) -> float:
    peak = equity[0] if equity else 0.0
    max_dd = 0.0
    for val in equity:
        peak = max(peak, val)
        if peak > 0:
            max_dd = max(max_dd, (peak - val) / peak)
    return max_dd


def _monte_carlo_from_trades(
    trades: list[Trade],
    initial_capital: float,
    *,
    n_simulations: int = 1000,
    seed: int = 42,
    ruin_drawdown_pct: float = 0.30,
) -> dict[str, Any]:
    pnls = np.array([float(t.pnl) for t in trades], dtype=float)
    if len(pnls) < 5:
        return {
            "simulations": 0,
            "reason": "trades_insuficientes",
            "risk_of_ruin_pct": None,
            "worst_sequence_return_pct": None,
            "equity_robustness_pct": None,
        }
    rng = np.random.default_rng(seed)
    returns: list[float] = []
    drawdowns: list[float] = []
    ruined = 0
    ruin_floor = initial_capital * (1 - ruin_drawdown_pct)
    for _ in range(n_simulations):
        sample = rng.permutation(pnls)
        equity = initial_capital
        curve = [equity]
        for pnl in sample:
            equity += pnl
            curve.append(equity)
        returns.append((equity / initial_capital - 1) if initial_capital else 0.0)
        dd = _max_drawdown_from_equity(curve)
        drawdowns.append(dd)
        if min(curve) <= ruin_floor:
            ruined += 1

    worst_sequence = sorted(pnls)
    equity = initial_capital
    worst_curve = [equity]
    for pnl in worst_sequence:
        equity += pnl
        worst_curve.append(equity)

    ret = np.array(returns)
    dd = np.array(drawdowns)
    return {
        "simulations": n_simulations,
        "return_p05_pct": round(float(np.percentile(ret, 5)) * 100, 2),
        "return_median_pct": round(float(np.median(ret)) * 100, 2),
        "return_p95_pct": round(float(np.percentile(ret, 95)) * 100, 2),
        "drawdown_p95_pct": round(float(np.percentile(dd, 95)) * 100, 2),
        "drawdown_median_pct": round(float(np.median(dd)) * 100, 2),
        "worst_sequence_return_pct": round(((equity / initial_capital) - 1) * 100, 2) if initial_capital else 0.0,
        "worst_sequence_drawdown_pct": round(_max_drawdown_from_equity(worst_curve) * 100, 2),
        "risk_of_ruin_pct": round((ruined / n_simulations) * 100, 2),
        "equity_robustness_pct": round(max(0.0, min(100.0, 100 - float(np.percentile(dd, 95)) * 180)), 2),
    }


def _monthly_concentration(trades: list[Trade]) -> float:
    buckets: dict[str, float] = defaultdict(float)
    for trade in trades:
        ts = trade.exit_time or trade.entry_time
        buckets[f"{ts.year}-{ts.month:02d}"] += abs(float(trade.pnl))
    total = sum(buckets.values())
    if total <= 0:
        return 1.0 if trades else 0.0
    return max(buckets.values()) / total


def _robustness_score(
    *,
    full: BacktestResult,
    oos: PerformanceReport,
    holdout: PerformanceReport | None,
    rolling: list[WalkForwardWindow],
    monte_carlo: dict[str, Any],
) -> dict[str, Any]:
    trades = len(full.trades)
    dd = max(float(oos.max_drawdown_pct), float(holdout.max_drawdown_pct if holdout else 0.0))
    concentration = _monthly_concentration(full.trades)
    positive_windows = [w for w in rolling if w.test.net_profit_pct > 0]
    window_stability = len(positive_windows) / len(rolling) if rolling else 0.0
    ruin = float(monte_carlo.get("risk_of_ruin_pct") or 0.0)

    score = 100.0
    if trades < 30:
        score -= (30 - trades) * 1.4
    elif trades < 60:
        score -= (60 - trades) * 0.35
    score -= min(dd * 100, 60) * 0.75
    score -= max(0.0, concentration - 0.25) * 80
    score -= (1 - window_stability) * 22
    score -= min(ruin, 50) * 0.8
    score = round(max(0.0, min(100.0, score)), 2)

    flags: list[str] = []
    if trades < 30:
        flags.append("poucos_trades")
    if dd > 0.20:
        flags.append("drawdown_alto")
    if concentration > 0.45:
        flags.append("performance_concentrada")
    if window_stability < 0.50 and rolling:
        flags.append("baixa_estabilidade_rolling")
    if ruin > 5:
        flags.append("risco_de_ruina_relevante")

    return {
        "score": score,
        "trade_count": trades,
        "max_validation_drawdown_pct": round(dd * 100, 2),
        "monthly_concentration_pct": round(concentration * 100, 2),
        "positive_rolling_windows_pct": round(window_stability * 100, 2),
        "risk_of_ruin_pct": ruin,
        "flags": flags,
        "approved": score >= 70 and not {"poucos_trades", "drawdown_alto", "risco_de_ruina_relevante"}.intersection(flags),
    }


def _promotion_checklist(
    *,
    backtest: PerformanceReport,
    oos: PerformanceReport,
    holdout: PerformanceReport | None,
    robustness: dict[str, Any],
) -> list[dict[str, Any]]:
    wf_ok = oos.net_profit_pct > 0 and oos.profit_factor >= 1.0 and oos.total_trades >= 5
    holdout_ok = holdout is not None and holdout.net_profit_pct > -0.05 and holdout.max_drawdown_pct < 0.25
    risk_ok = backtest.max_drawdown_pct < 0.20 and robustness.get("risk_of_ruin_pct", 100) <= 5
    return [
        {
            "label": "Backtest aprovado",
            "stage": "backtest",
            "ok": backtest.net_profit_pct > 0 and backtest.profit_factor >= 1.2 and backtest.total_trades >= 20,
            "value": f"Ret {backtest.net_profit_pct:.1%} · PF {backtest.profit_factor:.2f} · Trades {backtest.total_trades}",
        },
        {
            "label": "Walk-forward aprovado",
            "stage": "research",
            "ok": wf_ok,
            "value": f"OOS {oos.net_profit_pct:.1%} · PF {oos.profit_factor:.2f} · Trades {oos.total_trades}",
        },
        {
            "label": "Holdout final aprovado",
            "stage": "research",
            "ok": holdout_ok,
            "value": "Pendente" if holdout is None else f"Holdout {holdout.net_profit_pct:.1%} · DD {holdout.max_drawdown_pct:.1%}",
        },
        {
            "label": "Paper aprovado",
            "stage": "paper",
            "ok": False,
            "value": "Validar no paper após pesquisa aprovada",
        },
        {
            "label": "Risco aprovado",
            "stage": "risk",
            "ok": risk_ok,
            "value": f"DD {backtest.max_drawdown_pct:.1%} · Ruína {float(robustness.get('risk_of_ruin_pct') or 0):.1f}%",
        },
        {
            "label": "Live gates aprovados",
            "stage": "live",
            "ok": False,
            "value": "Validar API, saldo, reconciliação e kill switch antes do live",
        },
    ]


def run_walk_forward(config: AtlasConfig, df: pd.DataFrame, train_pct: float = 0.70) -> WalkForwardResult:
    if df.empty:
        raise ValueError("DataFrame vazio")
    warmup = int(config.strategy.params.get("warmup_bars", 205))
    n = len(df)
    holdout_pct = 0.15
    holdout_idx = max(warmup + 20, int(n * (1 - holdout_pct)))
    split_idx = max(warmup + 10, int(holdout_idx * train_pct))
    split_idx = min(split_idx, holdout_idx - 20)
    split_ts = df.index[split_idx]
    holdout_ts = df.index[holdout_idx] if holdout_idx < n else None

    is_df = df.iloc[:split_idx].copy()
    is_result = run_backtest_engine(config, is_df)

    oos_df = df.iloc[max(0, split_idx - warmup) : holdout_idx].copy()
    oos_full = run_backtest_engine(config, oos_df)
    oos_trades = _filter_oos_trades(oos_full, split_ts)

    split_dt = split_ts.to_pydatetime()
    oos_equity = [(ts, eq) for ts, eq in oos_full.equity_curve if ts >= split_dt]
    if not oos_equity:
        oos_equity = [(split_dt, config.risk.initial_capital)]

    oos_initial = oos_equity[0][1]
    oos_final = oos_equity[-1][1]
    is_stats = compute_statistics(is_result)
    oos_stats = _stats_from_trades_and_equity(oos_trades, oos_equity, oos_initial, oos_final)
    wfe = float(oos_stats.net_profit_pct / is_stats.net_profit_pct) if is_stats.net_profit_pct > 0 else None

    holdout_stats: PerformanceReport | None = None
    if holdout_ts is not None and holdout_idx < n - 5:
        holdout_stats = _slice_result_stats(config, df, start_idx=holdout_idx, end_idx=n, warmup=warmup)

    full_result = run_backtest_engine(config, df)
    rolling = _run_rolling_windows(config, df, warmup=warmup)
    monte_carlo = _monte_carlo_from_trades(full_result.trades, config.risk.initial_capital)
    robustness = _robustness_score(
        full=full_result,
        oos=oos_stats,
        holdout=holdout_stats,
        rolling=rolling,
        monte_carlo=monte_carlo,
    )
    checklist = _promotion_checklist(
        backtest=compute_statistics(full_result),
        oos=oos_stats,
        holdout=holdout_stats,
        robustness=robustness,
    )

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
        holdout=holdout_stats,
        holdout_trades=holdout_stats.total_trades if holdout_stats else 0,
        holdout_split_timestamp=str(holdout_ts) if holdout_ts is not None else None,
        rolling_windows=rolling,
        monte_carlo=monte_carlo,
        robustness=robustness,
        promotion_checklist=checklist,
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
        "holdout": wf.holdout.to_dict() if wf.holdout else None,
        "holdout_trades": wf.holdout_trades,
        "holdout_split_timestamp": wf.holdout_split_timestamp,
        "rolling_windows": [
            {
                "index": w.index,
                "train_start": w.train_start,
                "train_end": w.train_end,
                "test_start": w.test_start,
                "test_end": w.test_end,
                "train": w.train.to_dict(),
                "test": w.test.to_dict(),
                "test_trades": w.test_trades,
                "efficiency": w.efficiency,
            }
            for w in wf.rolling_windows
        ],
        "monte_carlo": wf.monte_carlo,
        "robustness": wf.robustness,
        "promotion_checklist": wf.promotion_checklist,
        "is_trades": wf.is_trades,
        "oos_trades": wf.oos_trades,
    }
