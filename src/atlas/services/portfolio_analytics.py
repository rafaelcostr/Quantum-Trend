"""Analytics consolidados para a página Portfolio."""
from __future__ import annotations

import math
import time
from typing import Any

from atlas.core.models import TradingMode
from atlas.research.reports import load_report_by_strategy_timeframe
from atlas.runtime.operational_config import load_paper_slots, slot_key
from atlas.runtime.risk_store import get_risk_settings
from atlas.runtime.state import build_positions, bot_state
from atlas.services.analytics import monthly_returns_from_equity
from atlas.services.demo_account import build_equity_curve, journal_entries, paper_metrics_for_dashboard, trade_stats
from atlas.services.quantum_service import compute_drawdown_curve
from atlas.strategies.mm200_trend_v2 import strategy_display_name

STRATEGY_SHORT: dict[str, str] = {
    "pullback_ema20_v1": "Pullback",
    "breakout_high20_v1": "Breakout",
    "supertrend_mm200_v1": "Supertrend",
}

_PORTFOLIO_CACHE: dict | None = None
_PORTFOLIO_CACHE_AT: float = 0.0
_PORTFOLIO_TTL = 30.0


def clear_portfolio_cache() -> None:
    global _PORTFOLIO_CACHE, _PORTFOLIO_CACHE_AT
    _PORTFOLIO_CACHE = None
    _PORTFOLIO_CACHE_AT = 0.0


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _metrics_from_report(report: dict | None) -> dict[str, float | int]:
    if not report:
        return {"pnl_pct": 0.0, "trades": 0, "win_rate_pct": 0.0, "profit_factor": 0.0, "max_drawdown_pct": 0.0}
    m = report.get("metrics") or report.get("statistics") or {}
    dd = float(m.get("max_drawdown_pct", m.get("max_drawdown", 0)) or 0)
    if dd <= 1:
        dd *= 100
    wr_raw = float(m.get("win_rate_pct", m.get("win_rate", 0)) or 0)
    win_rate_pct = wr_raw * 100 if wr_raw <= 1 else wr_raw
    ret = float(m.get("total_return_pct", m.get("net_profit_pct", 0)) or 0)
    if abs(ret) <= 1 and ret != 0:
        ret *= 100
    return {
        "pnl_pct": round(ret, 2),
        "trades": int(m.get("total_trades", m.get("trades", 0)) or 0),
        "win_rate_pct": round(win_rate_pct, 1),
        "profit_factor": round(float(m.get("profit_factor", 0) or 0), 2),
        "max_drawdown_pct": round(dd, 2),
    }


def _paper_trades_by_strategy(entries: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for e in entries:
        raw = str(e.get("strategy") or "").strip()
        key = raw or "unknown"
        for sid, label in STRATEGY_SHORT.items():
            if sid in raw or label.lower() in raw.lower():
                key = sid
                break
        grouped.setdefault(key, []).append(e)
    return grouped


def build_strategy_performance(*, slots, paper_entries: list[dict]) -> list[dict[str, Any]]:
    by_paper = _paper_trades_by_strategy(paper_entries)
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []

    for slot in slots:
        if not slot.enabled or slot.strategy in seen:
            continue
        seen.add(slot.strategy)
        paper_trades = by_paper.get(slot.strategy, [])
        if paper_trades:
            stats = trade_stats(paper_trades)
            rows.append(
                {
                    "strategy_id": slot.strategy,
                    "label": STRATEGY_SHORT.get(slot.strategy, strategy_display_name(slot.strategy)),
                    "timeframe": slot.timeframe.upper(),
                    "pnl_pct": round(float(stats.get("total_return_pct", 0) or 0), 2),
                    "trades": int(stats.get("trades", 0)),
                    "win_rate_pct": float(stats.get("win_rate", 0)),
                    "profit_factor": float(stats.get("pf", 0)),
                    "source": "paper",
                }
            )
            continue

        report = load_report_by_strategy_timeframe(slot.strategy, slot.timeframe)
        m = _metrics_from_report(report)
        rows.append(
            {
                "strategy_id": slot.strategy,
                "label": STRATEGY_SHORT.get(slot.strategy, strategy_display_name(slot.strategy)),
                "timeframe": slot.timeframe.upper(),
                "pnl_pct": m["pnl_pct"],
                "trades": m["trades"],
                "win_rate_pct": m["win_rate_pct"],
                "profit_factor": m["profit_factor"],
                "source": "backtest",
            }
        )

    defaults = [
        ("pullback_ema20_v1", "4h"),
        ("breakout_high20_v1", "4h"),
        ("supertrend_mm200_v1", "4h"),
    ]
    for sid, tf in defaults:
        if sid in seen:
            continue
        report = load_report_by_strategy_timeframe(sid, tf)
        if not report:
            continue
        m = _metrics_from_report(report)
        rows.append(
            {
                "strategy_id": sid,
                "label": STRATEGY_SHORT.get(sid, sid),
                "timeframe": tf.upper(),
                **m,
                "source": "backtest",
            }
        )
    return rows


def build_allocation(*, slots, positions, total_capital: float) -> list[dict[str, Any]]:
    if total_capital <= 0:
        return []

    enabled = [s for s in slots if s.enabled]
    if not enabled:
        enabled = slots

    weights: dict[str, float] = {s.strategy: 0.0 for s in enabled}
    for pos in positions:
        sid = next((s.strategy for s in enabled if strategy_display_name(s.strategy) == pos.strategy), None)
        if sid is None:
            for s in enabled:
                if STRATEGY_SHORT.get(s.strategy, "").lower() in pos.strategy.lower():
                    sid = s.strategy
                    break
        if sid:
            weights[sid] = weights.get(sid, 0.0) + max(float(pos.current), 0.0)

    if sum(weights.values()) <= 0:
        share = 100.0 / max(len(enabled), 1)
        return [
            {
                "label": STRATEGY_SHORT.get(s.strategy, strategy_display_name(s.strategy)),
                "strategy_id": s.strategy,
                "pct": round(share, 1),
            }
            for s in enabled
        ]

    total_w = sum(weights.values())
    return [
        {
            "label": STRATEGY_SHORT.get(sid, strategy_display_name(sid)),
            "strategy_id": sid,
            "pct": round(w / total_w * 100, 1),
        }
        for sid, w in weights.items()
        if w > 0
    ]


def _sharpe_from_equity(curve: list[dict]) -> float:
    vals = [float(r.get("equity", 0)) for r in curve if float(r.get("equity", 0)) > 0]
    if len(vals) < 3:
        return 0.0
    rets = [(vals[i] / vals[i - 1] - 1) for i in range(1, len(vals))]
    if not rets:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / len(rets)
    std = math.sqrt(var) if var > 0 else 0.0
    if std <= 0:
        return 0.0
    return round(mean / std * math.sqrt(min(252, len(rets))), 2)


def _volatility_pct(curve: list[dict]) -> float:
    vals = [float(r.get("equity", 0)) for r in curve if float(r.get("equity", 0)) > 0]
    if len(vals) < 2:
        return 0.0
    rets = [(vals[i] / vals[i - 1] - 1) * 100 for i in range(1, len(vals))]
    if not rets:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / len(rets)
    return round(math.sqrt(var), 2)


def portfolio_health_score(
    *,
    profit_factor: float,
    max_drawdown_pct: float,
    win_rate_pct: float,
    exposure_pct: float,
    consecutive_losses: int,
    volatility_pct: float,
) -> dict[str, Any]:
    score = (
        _clamp(profit_factor * 30) * 0.25
        + _clamp(100 - max_drawdown_pct * 3.5) * 0.25
        + _clamp(win_rate_pct) * 0.20
        + _clamp(100 - exposure_pct * 0.8) * 0.10
        + _clamp(100 - consecutive_losses * 12) * 0.10
        + _clamp(100 - volatility_pct * 2) * 0.10
    )
    score = round(_clamp(score), 0)
    if score >= 80:
        state, tone = "Saudável", "success"
    elif score >= 60:
        state, tone = "Atenção", "warning"
    else:
        state, tone = "Risco Elevado", "danger"
    return {
        "score": score,
        "state": state,
        "tone": tone,
        "components": {
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_drawdown_pct,
            "win_rate_pct": win_rate_pct,
            "exposure_pct": exposure_pct,
            "consecutive_losses": consecutive_losses,
            "volatility_pct": volatility_pct,
        },
    }


def _monthly_heatmap(monthly: list[dict]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in monthly[-12:]:
        ret = float(row.get("return_pct", row.get("r", 0)))
        label = str(row.get("month", row.get("m", "?")))
        short = label.split("/")[0] if "/" in label else label[:3]
        if ret >= 1.5:
            tone = "good"
        elif ret <= -1.0:
            tone = "bad"
        else:
            tone = "neutral"
        out.append({"month": short, "return_pct": round(ret, 2), "tone": tone})
    return out


def build_portfolio_analytics(
    *,
    balance: float,
    mode: TradingMode,
    initial_capital: float,
) -> dict[str, Any]:
    entries = journal_entries(mode=mode)
    equity_curve = build_equity_curve(entries, balance, mode=mode)
    drawdown_curve = compute_drawdown_curve(equity_curve)
    metrics = paper_metrics_for_dashboard(entries, balance) if balance > 0 else {}
    if balance > 0 and initial_capital > 0:
        metrics["total_return_pct"] = round((balance / initial_capital - 1) * 100, 2)
    metrics["sharpe"] = _sharpe_from_equity(equity_curve)

    dd_vals = [float(r.get("drawdown_pct", 0)) for r in drawdown_curve]
    current_dd = dd_vals[-1] if dd_vals else 0.0
    max_dd = max(dd_vals) if dd_vals else float(metrics.get("max_drawdown_pct", 0))

    slots = load_paper_slots()
    positions_dto = build_positions()
    positions = [
        {
            "asset": p.asset,
            "strategy": p.strategy,
            "entry": p.entry,
            "current": p.current,
            "pnl_pct": p.pnl_pct,
            "pnl": p.pnl,
            "side": p.side,
        }
        for p in positions_dto
    ]

    strategy_rows = build_strategy_performance(slots=slots, paper_entries=entries)
    allocation = build_allocation(slots=slots, positions=positions_dto, total_capital=balance)
    monthly = monthly_returns_from_equity(
        [{"timestamp": r.get("day", ""), "equity": r.get("equity", 0)} for r in equity_curve]
    )

    risk = get_risk_settings()
    health = portfolio_health_score(
        profit_factor=float(metrics.get("profit_factor", 0)),
        max_drawdown_pct=float(max_dd),
        win_rate_pct=float(metrics.get("win_rate_pct", 0)),
        exposure_pct=0.0,
        consecutive_losses=risk.consecutive_losses,
        volatility_pct=_volatility_pct(equity_curve),
    )

    return {
        "equity_curve": equity_curve,
        "drawdown_curve": drawdown_curve,
        "drawdown_summary": {"current_pct": round(current_dd, 2), "max_pct": round(max_dd, 2)},
        "strategy_performance": strategy_rows,
        "allocation": allocation,
        "open_positions_detail": positions,
        "portfolio_stats": {
            "win_rate_pct": float(metrics.get("win_rate_pct", 0)),
            "profit_factor": float(metrics.get("profit_factor", 0)),
            "total_return_pct": float(metrics.get("total_return_pct", 0)),
            "sharpe_ratio": float(metrics.get("sharpe", 0)),
            "max_drawdown_pct": round(float(max_dd), 2),
            "total_trades": int(metrics.get("trades", 0)),
        },
        "monthly_heatmap": _monthly_heatmap(monthly),
        "health": health,
    }


def get_enriched_portfolio_payload(base_payload: dict) -> dict:
    global _PORTFOLIO_CACHE, _PORTFOLIO_CACHE_AT
    now = time.time()
    if _PORTFOLIO_CACHE and (now - _PORTFOLIO_CACHE_AT) < _PORTFOLIO_TTL:
        return _PORTFOLIO_CACHE

    from atlas.runtime.operational_config import resolve_active_config

    live = bot_state.running and bot_state.mode == TradingMode.LIVE
    cfg = resolve_active_config(live_running=live)
    mode = TradingMode.LIVE if live else TradingMode.PAPER
    balance = float(base_payload.get("portfolio", {}).get("total_capital", cfg.risk.initial_capital))

    analytics = build_portfolio_analytics(
        balance=balance,
        mode=mode,
        initial_capital=cfg.risk.initial_capital,
    )
    exposure = float(base_payload.get("portfolio", {}).get("current_exposure_pct", 0))
    analytics["health"] = portfolio_health_score(
        profit_factor=float(analytics["portfolio_stats"]["profit_factor"]),
        max_drawdown_pct=float(analytics["drawdown_summary"]["max_pct"]),
        win_rate_pct=float(analytics["portfolio_stats"]["win_rate_pct"]),
        exposure_pct=exposure,
        consecutive_losses=int((base_payload.get("risk") or {}).get("consecutive_losses", 0)),
        volatility_pct=_volatility_pct(analytics["equity_curve"]),
    )

    merged = {**base_payload, **analytics}
    _PORTFOLIO_CACHE = merged
    _PORTFOLIO_CACHE_AT = now
    return merged
