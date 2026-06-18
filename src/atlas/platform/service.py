"""Agregador de payloads da plataforma para API e dashboard."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from atlas.platform.alerts import alert_center_payload
from atlas.platform.engine_monitor import collect_engine_metrics
from atlas.platform.state_machine import state_machine_payload
from atlas.platform.store import load_platform_state
from atlas.platform.stress_test import run_default_stress_suite
from atlas.services.quantum_service import get_quantum_status
from atlas.runtime.bot_runner import bot_pool
from atlas.runtime.state import bot_state


def get_platform_status() -> dict[str, Any]:
    state = load_platform_state()
    quantum = get_quantum_status()
    engine = collect_engine_metrics()
    sm = state_machine_payload()
    data_q = state.get("data_quality") or {}
    recovery = state.get("recovery") or {}
    scaling = state.get("capital_scaling") or {}

    strategy_health = float(quantum.get("health_score") or 0)
    engine_health = float(engine.get("score") or 0)
    data_health = float(data_q.get("score") or 0)
    system_health = round(strategy_health * 0.35 + engine_health * 0.35 + data_health * 0.30, 1)

    instances = bot_pool.snapshot_instances()
    next_analysis = None
    if instances:
        poll = instances[0].get("poll_seconds") or 60
        last = instances[0].get("last_tick_at")
        if last:
            next_analysis = f"~{poll}s após último tick"

    return {
        "system_health": system_health,
        "strategy_health": strategy_health,
        "engine_health": engine_health,
        "data_health": data_health,
        "alignment_score": quantum.get("alignment_score", 0),
        "alignment_breakdown": quantum.get("alignment_breakdown") or {},
        "regime": quantum.get("regime"),
        "regime_label": quantum.get("regime_label"),
        "runtime": {
            "state": sm.get("current"),
            "state_history": sm.get("history", [])[:10],
            "bot_running": bot_state.snapshot().get("running", False),
            "bot_mode": bot_state.mode.value if bot_state.mode else "paper",
            "last_decision": state.get("last_decision"),
            "last_sync": recovery.get("reconciled_at") or engine.get("last_sync"),
            "next_analysis": next_analysis,
            "risk_locked": state.get("risk_locked", False),
            "risk_lock_reason": state.get("risk_lock_reason"),
        },
        "recovery": recovery,
        "data_quality": data_q,
        "engine": engine,
        "alerts": alert_center_payload(),
        "score_explanation": state.get("latest_score_explanation"),
        "score_history": (state.get("score_explanations") or [])[:20],
        "capital_scaling": scaling,
        "trend_exhaustion": state.get("trend_exhaustion") or {},
        "decisions": (state.get("decisions") or [])[:15],
        "last_decision": state.get("last_decision"),
        "stress_reports": state.get("stress_reports") or [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def get_platform_dashboard_payload() -> dict[str, Any]:
    return get_platform_status()


def run_stress_tests() -> list[dict[str, Any]]:
    from atlas.core.env import project_root
    from pathlib import Path
    import pandas as pd

    cache = project_root() / "data" / "cache"
    df = None
    for name in ("binance_BTCUSDT_1d.csv", "binance_BTCUSDT_4h.csv", "binance_BTCUSDT_1h.csv"):
        path = cache / name
        if path.is_file():
            try:
                df = pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp")
                break
            except Exception:
                continue
    return run_default_stress_suite(df)
