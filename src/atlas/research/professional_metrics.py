from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from statistics import mean, pstdev
from typing import Any

import numpy as np

from atlas.core.config import AtlasConfig
from atlas.core.models import Trade
from atlas.research.engine_backtest import BacktestResult


@dataclass(frozen=True)
class EquityPoint:
    ts: datetime
    equity: float


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        val = float(value)
        if np.isfinite(val):
            return val
    except (TypeError, ValueError):
        pass
    return default


def _annualization_factor(timeframe: str) -> float:
    tf = timeframe.lower()
    if tf.endswith("m"):
        minutes = max(_safe_float(tf[:-1], 1), 1)
        return (365 * 24 * 60) / minutes
    if tf.endswith("h"):
        hours = max(_safe_float(tf[:-1], 1), 1)
        return (365 * 24) / hours
    if tf.endswith("d"):
        days = max(_safe_float(tf[:-1], 1), 1)
        return 365 / days
    return 365


def _equity_points(result: BacktestResult) -> list[EquityPoint]:
    return [EquityPoint(ts=ts, equity=_safe_float(eq)) for ts, eq in result.equity_curve]


def _returns(points: list[EquityPoint]) -> list[float]:
    out: list[float] = []
    for prev, cur in zip(points, points[1:]):
        if prev.equity > 0:
            out.append((cur.equity / prev.equity) - 1)
    return [r for r in out if np.isfinite(r)]


def _drawdown_stats(points: list[EquityPoint]) -> dict[str, Any]:
    peak = points[0].equity if points else 0.0
    max_dd = 0.0
    current_duration = 0
    max_duration = 0
    start: str | None = None
    max_start: str | None = None
    max_end: str | None = None

    for point in points:
        if point.equity >= peak:
            peak = point.equity
            current_duration = 0
            start = None
            continue
        current_duration += 1
        if start is None:
            start = point.ts.isoformat()
        dd = (peak - point.equity) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
            max_duration = current_duration
            max_start = start
            max_end = point.ts.isoformat()
        else:
            max_duration = max(max_duration, current_duration)

    return {
        "max_drawdown_pct": round(max_dd * 100, 4),
        "drawdown_duration_bars": max_duration,
        "drawdown_start": max_start,
        "drawdown_end": max_end,
    }


def _period_returns(points: list[EquityPoint], period: str) -> list[dict[str, Any]]:
    if not points:
        return []
    buckets: dict[str, list[float]] = defaultdict(list)
    for point in points:
        if period == "week":
            iso_year, iso_week, _ = point.ts.isocalendar()
            key = f"{iso_year}-W{iso_week:02d}"
        elif period == "year":
            key = f"{point.ts.year}"
        else:
            key = f"{point.ts.year}-{point.ts.month:02d}"
        buckets[key].append(point.equity)

    out: list[dict[str, Any]] = []
    previous_end: float | None = None
    for key in sorted(buckets):
        vals = buckets[key]
        start = previous_end if previous_end is not None else vals[0]
        end = vals[-1]
        ret = ((end / start) - 1) * 100 if start else 0.0
        out.append({"period": key, "return_pct": round(ret, 2), "start_equity": round(start, 2), "end_equity": round(end, 2)})
        previous_end = end
    return out


def _trade_periods(trades: list[Trade], key: str) -> list[dict[str, Any]]:
    buckets: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        ts = trade.exit_time or trade.entry_time
        if key == "asset":
            bucket = trade.symbol
        elif key == "timeframe":
            bucket = str(trade.metadata.get("timeframe") or "default")
        elif key == "regime":
            bucket = str(trade.metadata.get("regime") or trade.metadata.get("market_regime") or "unknown")
        else:
            bucket = "all"
        buckets[bucket].append(trade)
    return [_trade_bucket_stats(label, rows) for label, rows in sorted(buckets.items())]


def _trade_bucket_stats(label: str, trades: list[Trade]) -> dict[str, Any]:
    pnls = [_safe_float(t.pnl) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "bucket": label,
        "trades": len(trades),
        "net_pnl": round(sum(pnls), 2),
        "win_rate_pct": round((len(wins) / len(trades)) * 100, 2) if trades else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0),
    }


def compute_professional_analysis(result: BacktestResult, config: AtlasConfig | None = None) -> dict[str, Any]:
    points = _equity_points(result)
    trades = result.trades
    returns = _returns(points)
    annual = _annualization_factor(config.exchange.timeframe if config else "1d")
    total_return = (result.final_equity / result.initial_capital - 1) if result.initial_capital else 0.0
    dd = _drawdown_stats(points)
    max_dd = max(dd["max_drawdown_pct"] / 100, 0.0)

    sharpe = 0.0
    sortino = 0.0
    if len(returns) > 1 and pstdev(returns) > 0:
        sharpe = (mean(returns) / pstdev(returns)) * sqrt(annual)
        downside = [min(r, 0.0) for r in returns]
        downside_dev = pstdev(downside)
        sortino = (mean(returns) / downside_dev) * sqrt(annual) if downside_dev > 0 else 0.0

    pnls = [_safe_float(t.pnl) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    avg_win = mean(wins) if wins else 0.0
    avg_loss = abs(mean(losses)) if losses else 0.0
    win_rate = len(wins) / len(trades) if trades else 0.0
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss) if trades else 0.0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    net_profit = result.final_equity - result.initial_capital
    total_fees = sum(_safe_float(t.fees) for t in trades)
    exposure_bars = 0
    if points:
        index_by_ts = {p.ts: idx for idx, p in enumerate(points)}
        for t in trades:
            if t.exit_time is None:
                continue
            start = index_by_ts.get(t.entry_time)
            end = index_by_ts.get(t.exit_time)
            if start is not None and end is not None:
                exposure_bars += max(1, end - start)
    exposure_time_pct = (exposure_bars / len(points)) * 100 if points else 0.0
    turnover = sum((_safe_float(t.entry_price) * _safe_float(t.quantity)) for t in trades)
    if result.initial_capital > 0:
        turnover /= result.initial_capital

    sorted_returns = sorted(returns)
    var_95 = abs(np.percentile(sorted_returns, 5)) * 100 if sorted_returns else 0.0
    tail = [r for r in sorted_returns if r <= np.percentile(sorted_returns, 5)] if sorted_returns else []
    cvar_95 = abs(mean(tail)) * 100 if tail else 0.0

    costs = {
        "fee_rate": _safe_float(getattr(config.execution, "fee_rate", 0.0)) if config else 0.0,
        "maker_fee_rate": _safe_float(getattr(config.execution, "maker_fee_rate", None), _safe_float(getattr(config.execution, "fee_rate", 0.0))) if config else 0.0,
        "taker_fee_rate": _safe_float(getattr(config.execution, "taker_fee_rate", None), _safe_float(getattr(config.execution, "fee_rate", 0.0))) if config else 0.0,
        "slippage_rate": _safe_float(getattr(config.execution, "slippage_rate", 0.0)) if config else 0.0,
        "spread_rate": _safe_float(getattr(config.execution, "spread_rate", 0.0)) if config else 0.0,
        "funding_rate_daily": _safe_float(getattr(config.execution, "funding_rate_daily", 0.0)) if config else 0.0,
        "min_order_notional": _safe_float(getattr(config.execution, "min_order_notional", 0.0)) if config else 0.0,
        "quantity_step": _safe_float(getattr(config.execution, "quantity_step", 0.0)) if config else 0.0,
        "liquidity_notional": _safe_float(getattr(config.execution, "liquidity_notional", 0.0)) if config else 0.0,
        "total_fees": round(total_fees, 4),
        "fees_pct_of_initial": round((total_fees / result.initial_capital) * 100, 4) if result.initial_capital else 0.0,
    }

    overfitting = {
        "stability_score": _stability_score(total_return, max_dd, sharpe, len(trades)),
        "parameter_sensitivity": "unknown",
        "train_test_gap_pct": None,
        "flags": _overfit_flags(total_return, max_dd, sharpe, len(trades), returns),
    }

    return {
        "advanced_metrics": {
            "sharpe_ratio": round(sharpe, 4),
            "sortino_ratio": round(sortino, 4),
            "calmar_ratio": round((total_return / max_dd), 4) if max_dd > 0 else 0.0,
            "expectancy": round(expectancy, 4),
            "expectancy_pct": round(mean([_safe_float(t.pnl_pct) for t in trades]) * 100, 4) if trades else 0.0,
            "payoff_ratio": round(avg_win / avg_loss, 4) if avg_loss > 0 else (99.0 if avg_win > 0 else 0.0),
            "recovery_factor": round(net_profit / (max_dd * result.initial_capital), 4) if max_dd and result.initial_capital else 0.0,
            "drawdown_duration_bars": dd["drawdown_duration_bars"],
            "exposure_time_pct": round(exposure_time_pct, 2),
            "turnover": round(turnover, 4),
            "var_95_pct": round(var_95, 4),
            "cvar_95_pct": round(cvar_95, 4),
        },
        "costs": costs,
        "period_analysis": {
            "monthly": _period_returns(points, "month"),
            "weekly": _period_returns(points, "week"),
            "yearly": _period_returns(points, "year"),
            "by_asset": _trade_periods(trades, "asset"),
            "by_timeframe": _trade_periods(trades, "timeframe"),
            "by_regime": _trade_periods(trades, "regime"),
        },
        "overfitting": overfitting,
    }


def _stability_score(total_return: float, max_dd: float, sharpe: float, trades: int) -> float:
    score = 50.0
    score += min(max(total_return * 100, -30), 60) * 0.35
    score += min(max(sharpe, -2), 3) * 10
    score -= min(max_dd * 100, 60) * 0.45
    if trades < 30:
        score -= (30 - trades) * 0.8
    return round(max(0.0, min(100.0, score)), 2)


def _overfit_flags(total_return: float, max_dd: float, sharpe: float, trades: int, returns: list[float]) -> list[str]:
    flags: list[str] = []
    if trades < 30:
        flags.append("amostra_pequena")
    if max_dd > 0.25:
        flags.append("drawdown_alto")
    if sharpe > 3 and trades < 80:
        flags.append("sharpe_alto_com_poucos_trades")
    if len(returns) > 20 and pstdev(returns) > abs(mean(returns)) * 8:
        flags.append("retornos_instaveis")
    if total_return > 1.5 and trades < 40:
        flags.append("retorno_extremo_com_baixa_amostra")
    return flags
