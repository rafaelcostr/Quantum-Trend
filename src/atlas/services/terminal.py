from __future__ import annotations

import time

from atlas.brokers.binance import (
    credentials_configured,
    fetch_account_snapshot,
    fetch_tickers_cached,
    live_api_connected,
)
from atlas.core.config import default_config_for_mode, default_paper_config
from atlas.core.env import get_settings
from atlas.core.models import DashboardStats, StrategyDTO, TradingMode
from atlas.intelligence.dashboard import radar_from_metrics, strategy_status
from atlas.research.backtester import load_latest_report
from atlas.research.reports import load_report_by_strategy_timeframe
from atlas.services.demo_account import (
    account_breakdown,
    build_equity_curve,
    demo_snapshot,
    journal_entries,
    paper_metrics_for_dashboard,
    radar_from_paper,
    trade_stats,
)
from atlas.runtime.risk_store import get_risk_settings, update_risk_settings
from atlas.runtime.operational_config import operational_options
from atlas.runtime.system_store import get_runtime_system
from atlas.runtime.journal import Journal
from atlas.runtime.state import active_config, bot_state, build_positions
from atlas.runtime.live_gates import evaluate_live_gates
from atlas.services.quantum_service import compute_drawdown_curve, get_quantum_status
from atlas.platform.service import get_platform_dashboard_payload
from atlas.strategies.mm200_trend_v2 import strategy_display_name
from atlas.strategies.registry import list_strategies
from atlas.services.analytics import (
    extended_summary,
    load_trades_for_results,
    monthly_returns_from_equity,
    trade_distribution,
)


_DASHBOARD_CACHE: dict | None = None
_DASHBOARD_CACHE_AT: float = 0.0
_DASHBOARD_TTL = 45.0

_INTELLIGENCE_CACHE: dict | None = None
_INTELLIGENCE_CACHE_AT: float = 0.0
_INTELLIGENCE_TTL = 60.0


def clear_dashboard_cache() -> None:
    global _DASHBOARD_CACHE, _DASHBOARD_CACHE_AT
    _DASHBOARD_CACHE = None
    _DASHBOARD_CACHE_AT = 0.0


def clear_intelligence_cache() -> None:
    global _INTELLIGENCE_CACHE, _INTELLIGENCE_CACHE_AT
    _INTELLIGENCE_CACHE = None
    _INTELLIGENCE_CACHE_AT = 0.0


def _journal_realized_pnl(*, mode: TradingMode = TradingMode.PAPER) -> float:
    entries = journal_entries(mode=mode)
    return round(sum(float(e.get("pnl", 0)) for e in entries), 2)


def _resolve_account(
    *,
    live_active: bool,
    symbol: str,
    journal_mode: TradingMode,
) -> tuple[float, float, float, str, str, dict | None]:
    if live_active:
        snap = demo_snapshot(symbol, live=True) if credentials_configured(live=True) else None
        if snap:
            balance = snap.equity_usdt
            pnl = _journal_realized_pnl(mode=TradingMode.LIVE)
            cost_basis = balance - pnl
            pnl_pct = round((pnl / cost_basis) * 100, 2) if cost_basis > 0 else 0.0
            return balance, pnl, pnl_pct, "binance_live", "Binance Live", account_breakdown(snap)
        if credentials_configured(live=True):
            return 0.0, 0.0, 0.0, "api_error", "Binance Live (erro API)", None
        return 0.0, 0.0, 0.0, "unavailable", "Live (sem chaves)", None

    if not credentials_configured(live=False):
        return 0.0, 0.0, 0.0, "unavailable", "Binance Demo (sem chaves)", None

    snap = demo_snapshot(symbol, live=False)
    if snap:
        balance = snap.equity_usdt
        pnl = _journal_realized_pnl(mode=journal_mode)
        cost_basis = balance - pnl
        pnl_pct = round((pnl / cost_basis) * 100, 2) if cost_basis > 0 else 0.0
        return balance, pnl, pnl_pct, "binance_demo", "Binance Demo", account_breakdown(snap)
    return 0.0, 0.0, 0.0, "api_error", "Binance Demo (erro API)", None


def get_dashboard_payload() -> dict:
    global _DASHBOARD_CACHE, _DASHBOARD_CACHE_AT
    now = time.time()
    if _DASHBOARD_CACHE and (now - _DASHBOARD_CACHE_AT) < _DASHBOARD_TTL:
        return _DASHBOARD_CACHE

    cfg = active_config()
    live_active = bot_state.running and bot_state.mode == TradingMode.LIVE
    journal_mode = TradingMode.LIVE if live_active else TradingMode.PAPER
    entries = journal_entries(mode=journal_mode)

    balance, pnl, pnl_pct, balance_source, account_label, breakdown = _resolve_account(
        live_active=live_active,
        symbol=cfg.exchange.symbol,
        journal_mode=journal_mode,
    )

    metrics = paper_metrics_for_dashboard(entries, balance) if balance > 0 else {
        "win_rate_pct": 0.0,
        "profit_factor": 0.0,
        "max_drawdown_pct": 0.0,
        "atlas_score": 0,
        "trades": 0,
    }
    equity_display = (
        build_equity_curve(entries, balance, mode=journal_mode)
        if balance > 0
        else [{"day": "—", "equity": 0}]
    )
    if balance_source in {"binance_demo", "binance_live"} and balance > 0:
        from atlas.services.balance_history import load_balance_curve, record_balance

        if not load_balance_curve(mode=journal_mode):
            record_balance(mode=journal_mode, equity=balance, symbol=cfg.exchange.symbol)
    radar_data = radar_from_paper(entries, balance) if balance > 0 else radar_from_metrics(metrics)

    report = load_latest_report(active_config().strategy.name)
    flow_metrics = report["metrics"] if report and report.get("metrics") else metrics

    live_gates = evaluate_live_gates()
    quantum = get_quantum_status()
    positions = build_positions()
    stats = DashboardStats(
        balance=round(balance, 2),
        balance_delta_pct=round(pnl_pct, 2),
        pnl=round(pnl, 2),
        pnl_delta_pct=round(pnl_pct, 2),
        active_strategy=strategy_display_name(cfg.strategy.name),
        win_rate_pct=float(metrics.get("win_rate_pct", 0)),
        profit_factor=float(metrics.get("profit_factor", 0)),
        trades_today=get_risk_settings().trades_today if bot_state.running else 0,
        atlas_score=int(float(metrics.get("atlas_score", 0))),
        bot_running=bot_state.snapshot()["running"],
        bot_mode=bot_state.mode.value,
        kill_switch=get_settings().kill_switch_active,
        balance_source=balance_source,
        account_label=account_label,
        alignment_score=float(quantum.get("alignment_score") or 0),
        health_score=float(quantum.get("health_score") or 0),
        bot_phase=str(quantum.get("bot_phase") or "parado"),
        open_positions=len(positions),
    )

    payload = {
        "stats": stats.model_dump(),
        "equity_curve": equity_display,
        "drawdown_curve": compute_drawdown_curve(equity_display),
        "radar_data": radar_data,
        "positions": [p.model_dump() for p in positions],
        "flow": _promotion_flow(flow_metrics, live_gates, has_backtest=bool(report)),
        "account": breakdown,
        "quantum": quantum,
        "platform": get_platform_dashboard_payload(),
        "spark_up": _spark_from_equity(equity_display, up=True),
        "spark_down": _spark_from_equity(equity_display, up=False),
        "spark_mix": _spark_from_equity(equity_display, up=None),
    }
    _DASHBOARD_CACHE = payload
    _DASHBOARD_CACHE_AT = now
    return payload


def _spark_from_equity(equity: list[dict], up: bool | None) -> list[int]:
    vals = [e["equity"] for e in equity[-12:]]
    if len(vals) < 2:
        return [5, 6, 7, 8, 9, 10, 11, 12]
    base = vals[0]
    out = []
    for v in vals:
        delta = (v / base - 1) * 100
        if up is True:
            out.append(max(4, int(10 + delta)))
        elif up is False:
            out.append(max(4, int(12 - delta)))
        else:
            out.append(max(4, int(8 + delta / 2)))
    return out


def _promotion_flow(metrics: dict, live_gates: dict | None = None, *, has_backtest: bool = False) -> list[dict]:
    score = float(metrics.get("atlas_score", 0))
    pf = float(metrics.get("profit_factor", 0))
    gates = live_gates or evaluate_live_gates()
    live_running = bot_state.running and bot_state.mode == TradingMode.LIVE
    paper_running = bot_state.running and bot_state.mode == TradingMode.PAPER

    if live_running:
        live_status, live_pct = "Ativo", 100
    elif gates.get("eligible"):
        live_status, live_pct = "Pronto", 85
    elif pf >= 1.3 and gates.get("checks_passed", 0) >= gates.get("checks_total", 1) - 2:
        live_status, live_pct = "Quase pronto", 60
    else:
        live_status, live_pct = "Aguardando gates", max(0, int(gates.get("checks_passed", 0) / max(gates.get("checks_total", 1), 1) * 40))

    return [
        {
            "label": "Backtest",
            "status": "Concluído" if has_backtest else "Pendente",
            "pct": 100 if has_backtest else 0,
            "color": "#7C3AED",
        },
        {
            "label": "Validação Demo",
            "status": "Em andamento" if paper_running else ("Concluído" if gates.get("paper_days", 0) >= gates.get("min_paper_days", 7) else "Pendente"),
            "pct": min(100, 30 + gates.get("paper_days", 0) * 8) if not paper_running else 72,
            "color": "#3B82F6",
        },
        {
            "label": "Aprovação",
            "status": "Aprovado" if score >= 75 else "Pendente",
            "pct": min(100, int(score)),
            "color": "#F59E0B",
        },
        {
            "label": "Conta Real",
            "status": live_status,
            "pct": live_pct,
            "color": "#EF4444" if live_running else "#94a3b8",
        },
    ]


def get_strategies() -> list[StrategyDTO]:
    cfg = active_config()
    from atlas.strategies.metadata import is_entry_module_legacy, is_legacy_strategy

    out: list[StrategyDTO] = []
    for name in list_strategies(include_legacy=True):
        report = load_latest_report(name)
        legacy = is_legacy_strategy(name)
        entry_legacy = is_entry_module_legacy(name)
        if report:
            m = report["metrics"]
            score = float(m.get("atlas_score", 0))
            status = strategy_status(score, float(m.get("profit_factor", 0)), float(m.get("max_drawdown_pct", 0)))
            if entry_legacy:
                status = f"Módulo QTP · {status}"
            elif legacy:
                status = f"Legado · {status}"
            out.append(
                StrategyDTO(
                    id=name,
                    name=strategy_display_name(name),
                    winrate=float(m.get("win_rate_pct", 0)),
                    pf=float(m.get("profit_factor", 0)),
                    dd=float(m.get("max_drawdown_pct", 0)),
                    status=status,
                )
            )
        elif name == cfg.strategy.name:
            out.append(
                StrategyDTO(
                    id=name,
                    name=strategy_display_name(name),
                    winrate=0.0,
                    pf=0.0,
                    dd=0.0,
                    status=(
                        "Módulo QTP · sem backtest"
                        if entry_legacy
                        else "Legado · sem backtest"
                        if legacy
                        else "Sem backtest"
                    ),
                )
            )
        elif not legacy and not entry_legacy:
            out.append(
                StrategyDTO(
                    id=name,
                    name=strategy_display_name(name),
                    winrate=0.0,
                    pf=0.0,
                    dd=0.0,
                    status="Backtest pendente",
                )
            )
    return out


def get_journal_entries() -> list[dict]:
    mode = bot_state.mode if bot_state.running else TradingMode.PAPER
    events = Journal(database_url="", mode=mode).fetch_events(limit=300)
    enriched: list[dict] = []
    for ev in reversed(events):
        if ev.get("event") not in {"entry", "exit"}:
            continue
        payload = ev.get("payload") or {}
        enriched.append(
            {
                "ts": ev.get("ts"),
                "event": ev.get("event"),
                "symbol": ev.get("symbol"),
                "reason": payload.get("reason") or payload.get("signal"),
                "alignment_score": payload.get("alignment_score"),
                "regime_label": payload.get("regime_label"),
                "entry_module": payload.get("entry_module"),
                "indicators": payload.get("indicators"),
                "candle": payload.get("candle"),
                "fill": payload.get("fill"),
            }
        )
    if enriched:
        return enriched
    return journal_entries(mode=mode)


def get_intelligence_summary() -> dict:
    global _INTELLIGENCE_CACHE, _INTELLIGENCE_CACHE_AT
    now = time.time()
    if _INTELLIGENCE_CACHE and (now - _INTELLIGENCE_CACHE_AT) < _INTELLIGENCE_TTL:
        return _INTELLIGENCE_CACHE

    from atlas.services.intelligence_service import enrich_intelligence_summary

    strategies = get_strategies()
    tickers = fetch_tickers_cached(include_sparkline=False)
    best = max(strategies, key=lambda s: s.pf) if strategies else None
    heatmap = [
        {"sym": t.symbol, "score": int(min(100, max(0, 50 + t.change_pct * 5)))}
        for t in tickers
    ]
    cfg = active_config()
    report = load_latest_report(cfg.strategy.name)
    score = int(float(report["metrics"]["atlas_score"])) if report and report.get("metrics") else 0
    payload = {
        "strategies_evaluated": len(list_strategies()),
        "best_strategy": best.name if best else "—",
        "best_score": int(best.pf * 30) if best else 0,
        "overall_score": score,
        "strategies": [s.model_dump() for s in strategies],
        "heatmap": heatmap,
    }
    result = enrich_intelligence_summary(payload, cfg.strategy.name)
    _INTELLIGENCE_CACHE = result
    _INTELLIGENCE_CACHE_AT = now
    return result


def get_markets() -> list[dict]:
    return [t.model_dump() for t in fetch_tickers_cached(include_sparkline=True)]


def _paper_trade_stats() -> dict:
    entries = journal_entries(mode=TradingMode.PAPER)
    return trade_stats(entries)


def get_validation_payload() -> dict:
    from atlas.quantum.gates import promotion_checklist_paper

    cfg = default_paper_config()
    paper = _paper_trade_stats()
    snap = bot_state.snapshot()
    snap_demo = demo_snapshot(cfg.exchange.symbol, live=False)
    balance = snap_demo.equity_usdt if snap_demo else 0.0
    entries = journal_entries(mode=TradingMode.PAPER)
    equity = (
        build_equity_curve(entries, balance, mode=TradingMode.PAPER)
        if balance > 0
        else [{"day": "—", "equity": 0}]
    )

    paper_values = {
        "profit_factor": paper["pf"],
        "max_drawdown_pct": paper["dd"] / 100 if paper["dd"] > 1 else paper["dd"],
        "total_trades": paper["trades"],
        "win_rate": paper["win_rate"] / 100,
    }
    criteria = promotion_checklist_paper(paper_values)
    passed = sum(1 for c in criteria if c["ok"])
    score = min(100, int(passed / max(len(criteria), 1) * 100))

    return {
        "score": score,
        "criteria_passed": passed,
        "criteria_total": len(criteria),
        "criteria": [{"label": c["label"], "ok": c["ok"], "val": c["value"]} for c in criteria],
        "stats": {
            "pnl": paper["pnl"],
            "win_rate": paper["win_rate"],
            "profit_factor": paper["pf"],
            "drawdown": paper["dd"],
            "trades": paper["trades"],
            "days_running": snap.get("days_running", 0),
            "balance": round(balance, 2),
        },
        "bot_running": snap.get("running", False),
        "bot_mode": bot_state.mode.value,
        "live_gates": evaluate_live_gates(),
        "spark_up": _spark_from_equity(equity, True),
        "spark_down": _spark_from_equity(equity, False),
        "spark_mix": _spark_from_equity(equity, None),
    }


def get_risk_payload() -> dict:
    cfg = active_config()
    risk = get_risk_settings()
    live = bot_state.running and bot_state.mode == TradingMode.LIVE
    snap = fetch_account_snapshot(cfg.exchange.symbol, live=live)
    balance = snap.equity_usdt if snap else 0.0
    r = risk.to_dict()
    return {
        "settings": r,
        "balance": round(balance, 2),
        "summary": {
            "max_exposure": round(balance * r["risk_per_trade_pct"] / 100 * r["max_ops_per_day"], 0),
            "max_daily_loss": round(balance * r["daily_stop_pct"] / 100, 0),
            "daily_target": round(balance * r["daily_target_pct"] / 100, 0),
        },
        "protections": [
            "Stop diário",
            "Pausar após perdas",
            "Cooldown automático",
            "Kill switch global",
            f"Slippage máx {cfg.execution.slippage_rate * 100:.2f}%",
        ],
        "alert": "Drawdown elevado" if r["consecutive_losses"] >= r["pause_after_losses"] else None,
    }


def get_results_payload(*, strategy: str | None = None, timeframe: str | None = None) -> dict:
    cfg = active_config()
    strategy = strategy or cfg.strategy.name
    timeframe = (timeframe or cfg.exchange.timeframe).lower()
    symbol = cfg.exchange.symbol
    if strategy != cfg.strategy.name or timeframe != cfg.exchange.timeframe.lower():
        meta = load_report_by_strategy_timeframe(strategy, timeframe)
        if meta and meta.get("metadata", {}).get("market"):
            symbol = str(meta["metadata"]["market"])

    metrics, trades, equity = load_trades_for_results(strategy=strategy, timeframe=timeframe)
    period_start = equity[0]["day"] if equity else None
    period_end = equity[-1]["day"] if equity else None
    period_days = None
    if period_start and period_end:
        try:
            from datetime import date
            d0 = date.fromisoformat(period_start)
            d1 = date.fromisoformat(period_end)
            period_days = max(1, (d1 - d0).days)
        except ValueError:
            pass
    return {
        "title": f"{strategy_display_name(strategy)} · {symbol} · {timeframe}",
        "strategy": strategy,
        "timeframe": timeframe,
        "metrics": metrics,
        "equity_curve": equity[-120:],
        "monthly_returns": monthly_returns_from_equity(equity),
        "distribution": trade_distribution(trades),
        "period_start": period_start,
        "period_end": period_end,
        "period_days": period_days,
        "spark_up": _spark_from_equity(equity, True),
        "spark_mix": _spark_from_equity(equity, None),
    }


def get_reports_payload() -> dict:
    metrics, trades, equity = load_trades_for_results()
    return {
        "monthly_returns": monthly_returns_from_equity(equity),
        "equity_curve": equity[-90:],
        "summary": extended_summary(metrics),
    }


def get_settings_payload() -> dict:
    cfg = active_config()
    settings = get_settings()
    runtime = get_runtime_system()
    live_active = bot_state.running and bot_state.mode == TradingMode.LIVE
    demo_connected = credentials_configured(live=False) and fetch_account_snapshot(cfg.exchange.symbol, live=False) is not None
    live_connected = live_api_connected(default_config_for_mode(TradingMode.LIVE).exchange.symbol)
    opts = operational_options()
    notif_defaults = {
        "email_daily": True,
        "drawdown_alerts": True,
        "strategy_approval": True,
        "terminal_sounds": False,
        "telegram": bool(settings.telegram_bot_token and settings.telegram_chat_id),
    }
    notifications = {**notif_defaults, **runtime.notifications}
    return {
        "profile": {
            "name": "Operador",
            "email": "local@quantum-trend",
            "plan": "Atlas Live" if live_active else "Atlas Paper",
        },
        "exchanges": [
            {
                "name": "Binance Demo",
                "connected": demo_connected,
                "active": not live_active,
            },
            {
                "name": "Binance Live",
                "connected": live_connected or bool(settings.binance_live_api_key),
                "active": live_active,
            },
        ],
        "notifications": notifications,
        "telegram": {
            "configured": bool(settings.telegram_bot_token and settings.telegram_chat_id),
            "chat_id_set": bool(settings.telegram_chat_id),
        },
        "system": {
            "strategy": strategy_display_name(cfg.strategy.name),
            "strategy_id": cfg.strategy.name,
            "symbol": cfg.exchange.symbol,
            "timeframe": cfg.exchange.timeframe,
            "poll_seconds": cfg.runtime.poll_seconds,
            "kill_switch": settings.kill_switch_active,
            "bot_running": bot_state.snapshot()["running"],
            "bot_mode": bot_state.mode.value,
        },
        "operational": opts,
    }


def get_live_payload() -> dict:
    gates = evaluate_live_gates()
    snap = bot_state.snapshot()
    live_cfg = default_config_for_mode(TradingMode.LIVE)
    return {
        "gates": gates,
        "bot": snap,
        "config": {
            "symbol": live_cfg.exchange.symbol,
            "timeframe": live_cfg.exchange.timeframe,
            "strategy": strategy_display_name(live_cfg.strategy.name),
            "use_exchange_stop": live_cfg.execution.use_exchange_stop,
        },
        "instances": snap.get("instances", []),
    }

