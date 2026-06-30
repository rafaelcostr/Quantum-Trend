from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from atlas.brokers.binance import credentials_configured
from atlas.platform.engine_monitor import collect_engine_metrics
from atlas.platform.store import load_platform_state
from atlas.runtime.bot_runner import bot_pool
from atlas.runtime.state import bot_state

from atlas.monitoring.incident_manager import incidents_payload, open_incident, resolve_incident


def _latest_order() -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for slot, engine in bot_pool.engines():
        try:
            events = engine.journal.fetch_events(limit=80)
        except Exception:
            continue
        for event in events:
            if event.get("event") not in {"order_decision_after", "entry", "exit"}:
                continue
            row = {**event, "slot": slot}
            if latest is None or str(row.get("ts", "")) > str(latest.get("ts", "")):
                latest = row
    return latest


def _last_tick(instances: list[dict[str, Any]]) -> str | None:
    ticks = [str(i.get("last_tick_at")) for i in instances if i.get("last_tick_at")]
    return max(ticks) if ticks else None


def _stale_iso(value: str | None, *, seconds: int) -> bool:
    if not value:
        return True
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() > seconds
    except ValueError:
        return True


def _evaluate_incidents(panel: dict[str, Any]) -> None:
    bot = panel["bot"]
    binance = panel["binance"]
    regime = panel.get("regime") or {}
    recovery = panel.get("recovery") or {}
    last_error = panel.get("last_error")

    if not bot["active"]:
        open_incident(type="bot_stopped", message="Bot parado", module="runtime.bot_runner", severity="warning", key="bot:stopped")
    else:
        resolve_incident("bot:stopped", message="Bot voltou a operar", notify=False)

    if not binance["online"]:
        open_incident(type="binance_offline", message="Binance sem resposta", module="brokers.binance", severity="critical", key="binance:offline")
    else:
        resolve_incident("binance:offline", message="Binance online", notify=False)

    if last_error:
        open_incident(type="runtime_error", message=str(last_error), module="runtime.engine", severity="critical", key=f"runtime:error:{str(last_error)[:80]}")

    if recovery.get("warning") or recovery.get("risk_locked"):
        open_incident(
            type="exchange_divergence",
            message=str(recovery.get("warning") or recovery.get("risk_lock_reason") or "Divergência com exchange"),
            module="runtime.reconciler",
            severity="critical",
            key="reconciler:divergence",
            metadata=recovery,
        )
    else:
        resolve_incident("reconciler:divergence", message="Reconciliação normalizada", notify=False)

    if regime.get("stale"):
        open_incident(type="regime_stale", message="Regime de mercado desatualizado", module="services.market_regime", severity="warning", key="market_regime:stale", metadata=regime)
    else:
        resolve_incident("market_regime:stale", message="Regime atualizado", notify=False)


def monitoring_health_payload(*, evaluate: bool = True) -> dict[str, Any]:
    engine = collect_engine_metrics()
    platform = load_platform_state()
    recovery = platform.get("recovery") or {}
    data_quality = platform.get("data_quality") or {}
    instances = engine.get("instances") or bot_pool.snapshot_instances()
    bot_snapshot = bot_state.snapshot()
    live = bot_snapshot.get("mode") == "live"
    last_order = _latest_order()
    last_tick = _last_tick(instances) or bot_snapshot.get("last_tick_at")
    last_error = bot_snapshot.get("last_error") or next((i.get("last_error") for i in instances if i.get("last_error")), None)
    binance_online = engine.get("broker_status") == "connected"

    regime_stale = bool(data_quality.get("regime_stale") or data_quality.get("stale"))
    panel = {
        "api": {
            "online": True,
            "status": "ok",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        },
        "binance": {
            "online": binance_online,
            "status": engine.get("broker_status"),
            "latency_ms": engine.get("binance_latency_ms"),
            "credentials_configured": credentials_configured(live=live),
        },
        "bot": {
            "active": bool(bot_snapshot.get("running")),
            "mode": bot_snapshot.get("mode"),
            "instance_count": bot_snapshot.get("instance_count", 0),
            "instances": instances,
        },
        "last_tick_at": last_tick,
        "last_order": last_order,
        "last_reconciliation_at": recovery.get("reconciled_at") or engine.get("last_sync"),
        "last_error": last_error,
        "recovery": recovery,
        "regime": {
            "stale": regime_stale,
            "last_candle_ts": engine.get("last_candle_ts"),
            "candle_count": engine.get("candle_count"),
        },
        "health": {
            "score": engine.get("score", 0),
            "issues": engine.get("issues", []),
            "last_tick_stale": _stale_iso(last_tick, seconds=1800) if bot_snapshot.get("running") else False,
            "last_reconciliation_stale": _stale_iso(recovery.get("reconciled_at") or engine.get("last_sync"), seconds=3600),
        },
    }
    if evaluate:
        _evaluate_incidents(panel)
    panel["incidents"] = incidents_payload()
    return panel
