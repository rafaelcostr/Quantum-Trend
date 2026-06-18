from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

from atlas.intelligence.metrics import compute_cagr, infer_initial_capital, years_tested


def _parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def compute_sortino(equity_curve: list[dict[str, Any]]) -> float | None:
    if len(equity_curve) < 3:
        return None
    equities = np.array([float(p["equity"]) for p in equity_curve])
    returns = np.diff(equities) / equities[:-1]
    returns = returns[np.isfinite(returns)]
    if len(returns) < 2:
        return None
    downside = returns[returns < 0]
    if len(downside) < 1 or downside.std() == 0:
        return None
    return float((returns.mean() / downside.std()) * np.sqrt(365 * 6))


def compute_payoff_ratio(trades: list[dict[str, Any]]) -> float | None:
    wins = [float(t["pnl"]) for t in trades if float(t.get("pnl", 0)) > 0]
    losses = [abs(float(t["pnl"])) for t in trades if float(t.get("pnl", 0)) <= 0]
    if not wins or not losses:
        return None
    return float(np.mean(wins) / np.mean(losses))


def compute_recovery_factor(net_profit: float, max_dd_pct: float, initial_capital: float) -> float | None:
    max_dd_usd = max_dd_pct * initial_capital
    if max_dd_usd <= 0:
        return None
    return float(net_profit / max_dd_usd)


def compute_calmar(cagr: float | None, max_dd_pct: float) -> float | None:
    if cagr is None or max_dd_pct <= 0:
        return None
    return float(cagr / max_dd_pct)


def compute_market_exposure(
    trades: list[dict[str, Any]],
    equity_curve: list[dict[str, Any]],
) -> float | None:
    if not trades:
        return None

    start = end = None
    if len(equity_curve) >= 2:
        start = _parse_ts(str(equity_curve[0].get("timestamp", "")))
        end = _parse_ts(str(equity_curve[-1].get("timestamp", "")))

    if not start or not end:
        entry_times = [_parse_ts(str(t.get("entry_time", ""))) for t in trades]
        exit_times = [_parse_ts(str(t.get("exit_time", ""))) for t in trades]
        entry_times = [t for t in entry_times if t]
        exit_times = [t for t in exit_times if t]
        if not entry_times or not exit_times:
            return None
        start = min(entry_times)
        end = max(exit_times)

    total_seconds = (end - start).total_seconds()
    if total_seconds <= 0:
        return None

    in_market = 0.0
    for t in trades:
        entry = _parse_ts(str(t.get("entry_time", "")))
        exit_ = _parse_ts(str(t.get("exit_time", "")))
        if entry and exit_ and exit_ > entry:
            in_market += (exit_ - entry).total_seconds()

    return float(min(1.0, in_market / total_seconds))


def compute_streaks(trades: list[dict[str, Any]]) -> tuple[int, int]:
    max_win = max_loss = 0
    cur_win = cur_loss = 0
    for t in trades:
        pnl = float(t.get("pnl", 0))
        if pnl > 0:
            cur_win += 1
            cur_loss = 0
            max_win = max(max_win, cur_win)
        else:
            cur_loss += 1
            cur_win = 0
            max_loss = max(max_loss, cur_loss)
    return max_win, max_loss


def build_level2_values(bundle) -> dict[str, Any]:
    stats = bundle.statistics
    initial = infer_initial_capital(stats, bundle.trades, bundle.equity_curve)
    net_profit = float(stats.get("net_profit", 0))
    net_pct = float(stats.get("net_profit_pct", 0))
    max_dd = float(stats.get("max_drawdown_pct", 0))
    cagr = compute_cagr(bundle.equity_curve, net_pct)

    max_win, max_loss = compute_streaks(bundle.trades)

    return {
        "sortino_ratio": compute_sortino(bundle.equity_curve),
        "recovery_factor": compute_recovery_factor(net_profit, max_dd, initial),
        "payoff_ratio": compute_payoff_ratio(bundle.trades),
        "calmar_ratio": compute_calmar(cagr, max_dd),
        "market_exposure": compute_market_exposure(bundle.trades, bundle.equity_curve),
        "max_win_streak": max_win,
        "max_loss_streak": max_loss,
        "cagr": cagr,
        "years_tested": years_tested(bundle.equity_curve),
    }
