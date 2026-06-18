"""Serviços QuantumTrend Pro — portfolio, status e métricas institucionais."""
from __future__ import annotations

from datetime import datetime, timezone

from atlas.core.models import TradingMode
from atlas.quantum.health import StrategyHealthMonitor
from atlas.quantum.portfolio import build_portfolio_snapshot
from atlas.quantum.runtime_store import get_runtime_snapshot
from atlas.research.backtester import load_latest_report
from atlas.research.reports import load_report_by_strategy_timeframe
from atlas.runtime.state import active_config, bot_state
from atlas.services.demo_account import demo_snapshot, journal_entries, trade_stats
from atlas.services.analytics import monthly_returns_from_equity
from atlas.runtime.risk_store import get_risk_settings


def resolve_bot_phase() -> str:
    snap = bot_state.snapshot()
    if not snap.get("running"):
        return "parado"
    if bot_state.mode == TradingMode.LIVE:
        return "operando"
    if snap.get("in_position"):
        return "operando"
    return "demo"


def get_quantum_status() -> dict:
    cfg = active_config()
    runtime = get_runtime_snapshot()
    phase = runtime.get("bot_phase") or resolve_bot_phase()
    report = load_latest_report(cfg.strategy.name)
    health_score = float(runtime.get("health_score") or 0)
    if report and health_score <= 0:
        try:
            stats = report.get("statistics") or {}
            trades_raw = report.get("trades") or []
            from atlas.core.models import Trade

            parsed: list[Trade] = []
            for raw in trades_raw:
                if not isinstance(raw, dict):
                    continue
                try:
                    parsed.append(Trade.model_validate(raw))
                except Exception:
                    continue
            curve = []
            for row in report.get("equity_curve") or []:
                if not isinstance(row, dict):
                    continue
                ts = row.get("timestamp")
                eq = row.get("equity")
                if ts is None or eq is None:
                    continue
                curve.append(
                    (
                        datetime.fromisoformat(str(ts).replace("Z", "+00:00")),
                        float(eq),
                    )
                )
            if parsed:
                health = StrategyHealthMonitor().evaluate(parsed, equity_curve=curve)
                health_score = health.health_score
        except Exception:
            pass

    return {
        "strategy": cfg.strategy.name,
        "bot_phase": phase,
        "alignment_score": runtime.get("alignment_score", 0),
        "alignment_breakdown": runtime.get("alignment_breakdown") or {},
        "alignment_history": runtime.get("alignment_history") or [],
        "health_score": health_score,
        "health_history": runtime.get("health_history") or [],
        "regime": runtime.get("regime"),
        "regime_label": runtime.get("regime_label"),
        "last_signal": runtime.get("last_signal"),
        "last_reason": runtime.get("last_reason"),
        "entry_module": runtime.get("entry_module"),
        "entry_confidence": runtime.get("entry_confidence"),
        "entry_result": runtime.get("entry_result"),
        "module_status": runtime.get("module_status") or _default_module_status(),
        "module_health": runtime.get("module_health") or _module_health_from_report(report),
        "module_backtest_stats": _module_stats_from_report(report),
        "rejected_modules": runtime.get("rejected_modules") or [],
        "updated_at": runtime.get("updated_at"),
    }


def _default_module_status() -> dict[str, dict[str, object]]:
    return {
        "pullback": {"active": True, "triggered": False, "confidence": None, "reason": "sem gatilho"},
        "breakout": {"active": True, "triggered": False, "confidence": None, "reason": "sem gatilho"},
        "supertrend": {"active": True, "triggered": False, "confidence": None, "reason": "sem gatilho"},
    }


def _module_stats_from_report(report: dict | None) -> dict[str, dict[str, float | int]]:
    if not report:
        return {}
    meta = report.get("metadata") or {}
    stats = meta.get("module_stats") or report.get("module_stats")
    return stats if isinstance(stats, dict) else {}


def _module_health_from_report(report: dict | None) -> dict[str, float]:
    stats = _module_stats_from_report(report)
    if not stats:
        return {}
    return {
        mod: float(data.get("health_score") or 0)
        for mod, data in stats.items()
        if isinstance(data, dict)
    }


def get_portfolio_payload() -> dict:
    cfg = active_config()
    live = bot_state.running and bot_state.mode == TradingMode.LIVE
    mode = TradingMode.LIVE if live else TradingMode.PAPER
    snap = demo_snapshot(cfg.exchange.symbol, live=live)
    balance = snap.equity_usdt if snap else cfg.risk.initial_capital
    cash = snap.quote_free if snap else balance
    allocated = (snap.base_total * (snap.mark_price or 0)) if snap and snap.base_total else 0.0
    entries = journal_entries(mode=mode)
    stats = trade_stats(entries)
    risk = get_risk_settings()

    started = None
    if bot_state.started_at:
        started = bot_state.started_at

    portfolio = build_portfolio_snapshot(
        equity=balance,
        cash=cash,
        allocated=allocated,
        daily_pnl=risk.daily_pnl,
        initial_capital=cfg.risk.initial_capital,
        started_at=started,
    )

    report = load_report_by_strategy_timeframe(cfg.strategy.name, "1h") or load_latest_report(cfg.strategy.name)
    monthly: list[dict] = []
    if report and report.get("equity_curve"):
        monthly = monthly_returns_from_equity(report["equity_curve"])

    base = {
        "portfolio": portfolio.__dict__,
        "open_positions": len([e for e in entries if float(e.get("pnl", 0)) == 0]),
        "stats_30d": stats,
        "monthly_returns": monthly[-12:],
        "risk": risk.to_dict(),
    }

    from atlas.services.portfolio_analytics import get_enriched_portfolio_payload

    return get_enriched_portfolio_payload(base)


def compute_drawdown_curve(equity_curve: list[dict]) -> list[dict]:
    out: list[dict] = []
    peak = 0.0
    for row in equity_curve:
        eq = float(row.get("equity", 0))
        label = row.get("day") or row.get("timestamp") or ""
        peak = max(peak, eq)
        dd = ((peak - eq) / peak * 100) if peak > 0 else 0.0
        out.append({"day": str(label)[:10], "drawdown_pct": round(dd, 2)})
    return out
