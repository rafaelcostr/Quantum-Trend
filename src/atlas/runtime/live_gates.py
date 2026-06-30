from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

from atlas.brokers.binance import credentials_configured, fetch_account_snapshot
from atlas.core.config import default_config_for_mode
from atlas.core.env import get_settings
from atlas.core.models import TradingMode
from atlas.intelligence.diagnostics import promotion_checklist_backtest_paper
from atlas.intelligence.research_store import load_walkforward
from atlas.research.backtester import load_latest_report
from atlas.runtime.journal import Journal
from atlas.runtime.operational_config import resolve_active_config

_LIVE_GATES_CACHE: dict[str, Any] | None = None
_LIVE_GATES_CACHE_AT: float = 0.0
_LIVE_GATES_TTL = 90.0


def clear_live_gates_cache() -> None:
    global _LIVE_GATES_CACHE, _LIVE_GATES_CACHE_AT
    _LIVE_GATES_CACHE = None
    _LIVE_GATES_CACHE_AT = 0.0


def _level3_gate_values(strategy: str) -> dict[str, Any] | None:
    from atlas.core.env import project_root

    wf = load_walkforward(project_root() / "data" / "reports", strategy)
    if not wf:
        return None
    oos = wf.get("out_of_sample", {})
    return {
        "oos_return": oos.get("net_profit_pct"),
        "oos_profit_factor": oos.get("profit_factor"),
    }


def _min_paper_days() -> int:
    raw = os.getenv("ATLAS_LIVE_MIN_PAPER_DAYS", "7").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 7


def _live_opt_in() -> bool:
    return os.getenv("ATLAS_ALLOW_LIVE", "0").strip().lower() in {"1", "true", "yes", "on"}


def _min_live_balance() -> float:
    raw = os.getenv("ATLAS_LIVE_MIN_BALANCE_USDT", "25").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 25.0


def _recent_operational_error() -> str | None:
    events = Journal(database_url="", mode=TradingMode.PAPER).fetch_events(limit=100)
    for ev in events:
        if ev.get("event") == "error":
            payload = ev.get("payload") or {}
            return str(payload.get("error") or "erro operacional recente")[:180]
    return None


def _paper_drawdown_pct() -> float:
    from atlas.services.demo_account import journal_entries, trade_stats

    stats = trade_stats(journal_entries(mode=TradingMode.PAPER))
    return float(stats.get("dd") or 0)


def _risk_configured() -> tuple[bool, str]:
    from atlas.runtime.risk_store import get_risk_settings

    risk = get_risk_settings()
    if risk.risk_per_trade_pct <= 0:
        return False, "risk_per_trade_pct precisa ser > 0"
    if risk.daily_stop_pct <= 0:
        return False, "daily_stop_pct precisa ser > 0"
    if risk.max_ops_per_day <= 0:
        return False, "max_ops_per_day precisa ser > 0"
    return True, "ok"


def _reconciliation_ok() -> tuple[bool, str]:
    from atlas.platform.store import load_platform_state

    state = load_platform_state()
    recovery = state.get("recovery") or {}
    issues = recovery.get("issues") or []
    if issues:
        return False, "; ".join(map(str, issues[:2]))
    if recovery.get("open_orders"):
        return False, "existem ordens abertas pendentes"
    return True, recovery.get("reconciled_at") or "sem pendências"


def _paper_days_running() -> int:
    from atlas.runtime.state import bot_state

    snap = bot_state.snapshot()
    if bot_state.mode == TradingMode.PAPER and bot_state.running and snap.get("started_at"):
        started = datetime.fromisoformat(snap["started_at"])
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - started).days)

    events = Journal(database_url="", mode=TradingMode.PAPER).fetch_events(limit=5000)
    if not events:
        return 0
    first_ts = events[0].get("ts")
    if not first_ts:
        return 0
    started = datetime.fromisoformat(str(first_ts).replace("Z", "+00:00"))
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - started).days)


def _backtest_values(cfg_strategy: str) -> dict[str, Any] | None:
    report = load_latest_report(cfg_strategy)
    if not report or not report.get("metrics"):
        return None
    metrics = dict(report["metrics"])
    if "total_trades" not in metrics and "trades" in metrics:
        metrics["total_trades"] = metrics["trades"]
    if "sharpe_ratio" not in metrics and "sharpe" in metrics:
        metrics["sharpe_ratio"] = metrics["sharpe"]
    # Relatórios quick usam DD em % (ex.: 5.13); checklist espera decimal (0.0513)
    dd = float(metrics.get("max_drawdown_pct", 0))
    if dd > 1:
        metrics["max_drawdown_pct"] = dd / 100
    return metrics


def evaluate_live_gates() -> dict[str, Any]:
    """Checklist obrigatório antes de habilitar trading live."""
    global _LIVE_GATES_CACHE, _LIVE_GATES_CACHE_AT
    now = time.time()
    if _LIVE_GATES_CACHE and (now - _LIVE_GATES_CACHE_AT) < _LIVE_GATES_TTL:
        return _LIVE_GATES_CACHE

    from atlas.runtime.state import bot_state

    cfg = resolve_active_config(live_running=False)
    live_cfg = resolve_active_config(live_running=True)
    settings = get_settings()
    checks: list[dict[str, Any]] = []
    blocking: list[str] = []

    def add(label: str, ok: bool, value: str) -> None:
        checks.append({"label": label, "ok": ok, "value": value})
        if not ok:
            blocking.append(label)

    add(
        "Opt-in ATLAS_ALLOW_LIVE=1",
        _live_opt_in(),
        "habilitado" if _live_opt_in() else "defina ATLAS_ALLOW_LIVE=1 no .env",
    )
    add(
        "Kill switch desligado",
        not settings.kill_switch_active,
        "ativo" if settings.kill_switch_active else "inativo",
    )
    add(
        "Chaves Binance Live configuradas",
        credentials_configured(live=True),
        "ok" if credentials_configured(live=True) else "BINANCE_LIVE_API_* ausentes",
    )

    live_snap = None
    if credentials_configured(live=True):
        live_snap = fetch_account_snapshot(live_cfg.exchange.symbol, live=True)
    add(
        "Conexão Binance Live",
        live_snap is not None,
        "conectada" if live_snap else "falha ao ler saldo live",
    )
    min_balance = _min_live_balance()
    live_balance = float(live_snap.equity_usdt) if live_snap else 0.0
    add(
        f"Saldo live mínimo ≥ ${min_balance:.0f}",
        live_balance >= min_balance,
        f"${live_balance:.2f}",
    )

    add(
        "API saudável",
        credentials_configured(live=False) or credentials_configured(live=True),
        "credenciais presentes" if credentials_configured(live=False) or credentials_configured(live=True) else "sem credenciais",
    )

    risk_ok, risk_value = _risk_configured()
    add("Risco configurado", risk_ok, risk_value)

    rec_ok, rec_value = _reconciliation_ok()
    add("Reconciliação sem pendências", rec_ok, rec_value)

    recent_error = _recent_operational_error()
    add(
        "Sem erro operacional recente",
        recent_error is None,
        "ok" if recent_error is None else recent_error,
    )

    add(
        "Bot paper não está rodando",
        not (bot_state.running and bot_state.mode == TradingMode.PAPER),
        "paper parado" if not bot_state.running or bot_state.mode != TradingMode.PAPER else "pare o paper antes",
    )
    add(
        "Bot live não está rodando",
        not (bot_state.running and bot_state.mode == TradingMode.LIVE),
        "live parado" if not bot_state.running or bot_state.mode != TradingMode.LIVE else "live já ativo",
    )

    min_days = _min_paper_days()
    paper_days = _paper_days_running()
    add(
        f"Paper rodando ≥ {min_days} dias",
        paper_days >= min_days,
        f"{paper_days} / {min_days} dias",
    )

    max_dd = float(os.getenv("ATLAS_LIVE_MAX_PAPER_DD_PCT", "15") or 15)
    paper_dd = _paper_drawdown_pct()
    add(
        f"Drawdown paper ≤ {max_dd:.1f}%",
        paper_dd <= max_dd,
        f"{paper_dd:.2f}%",
    )

    metrics = _backtest_values(cfg.strategy.name)
    l3_values = _level3_gate_values(cfg.strategy.name)

    if metrics:
        promo = promotion_checklist_backtest_paper(metrics, level3_values=l3_values)
        for item in promo:
            add(item["label"], bool(item["ok"]), str(item["value"]))
    else:
        add("Relatório de backtest disponível", False, "rode um backtest primeiro")

    eligible = len(blocking) == 0
    payload = {
        "eligible": eligible,
        "checks": checks,
        "checks_passed": sum(1 for c in checks if c["ok"]),
        "checks_total": len(checks),
        "blocking_reasons": blocking,
        "paper_days": paper_days,
        "min_paper_days": min_days,
        "live_symbol": live_cfg.exchange.symbol,
        "live_strategy": live_cfg.strategy.name,
        "requires_opt_in": True,
    }
    _LIVE_GATES_CACHE = payload
    _LIVE_GATES_CACHE_AT = now
    return payload
