"""Engine Monitor — saúde operacional da infraestrutura."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

from atlas.brokers.binance import credentials_configured, demo_api_connected, live_api_connected
from atlas.core.env import project_root
from atlas.platform.store import patch_platform_state
from atlas.runtime.bot_runner import bot_pool
from atlas.runtime.state import bot_state


def _resource_usage() -> dict[str, float | None]:
    mem_mb: float | None = None
    cpu_pct: float | None = None
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        mem_mb = round(usage.ru_maxrss / 1024, 1)  # Linux KB → MB approx
    except Exception:
        pass
    return {"memory_mb": mem_mb, "cpu_pct": cpu_pct}


def _binance_latency_ms(*, live: bool = False) -> float | None:
    t0 = time.perf_counter()
    try:
        ok = live_api_connected() if live else demo_api_connected()
        if not ok:
            return None
        return round((time.perf_counter() - t0) * 1000, 1)
    except Exception:
        return None


def collect_engine_metrics() -> dict[str, Any]:
    instances = bot_pool.snapshot_instances()
    live = bot_state.running and bot_state.mode and bot_state.mode.value == "live"
    platform = __import__("atlas.platform.store", fromlist=["load_platform_state"]).load_platform_state()
    recovery = platform.get("recovery") or {}
    data_q = platform.get("data_quality") or {}

    last_sync = recovery.get("reconciled_at") or platform.get("updated_at")
    last_candle = data_q.get("last_candle_ts")
    candle_count = data_q.get("candle_count", 0)

    score = 100.0
    issues: list[str] = []

    if bot_state.running and not instances:
        score -= 30
        issues.append("bot marcado como running sem instâncias")
    for inst in instances:
        if inst.get("last_error"):
            score -= 15
            issues.append(f"erro em {inst.get('key')}")
        if inst.get("alive") is False:
            score -= 25
            issues.append(f"runner morto: {inst.get('key')}")

    latency = _binance_latency_ms(live=live)
    if latency is None and credentials_configured(live=live):
        score -= 20
        issues.append("Binance indisponível")
    elif latency is not None and latency > 3000:
        score -= 10
        issues.append(f"latência alta ({latency}ms)")

    if data_q.get("score", 100) < 70:
        score -= 15
        issues.append("data quality baixa")

    if recovery.get("risk_locked"):
        score -= 20
        issues.append("recovery pendente")

    score = max(0.0, min(100.0, round(score, 1)))

    payload = {
        "score": score,
        "issues": issues,
        "binance_latency_ms": latency,
        "last_sync": last_sync,
        "last_candle_ts": last_candle,
        "candle_count": candle_count,
        "instances": instances,
        "instance_count": len(instances),
        "bot_running": bot_state.snapshot().get("running", False),
        "broker_status": "connected" if latency is not None else "disconnected",
        "api_status": "ok",
        "recovery_status": "ok" if recovery.get("ok", True) else "attention",
        "data_quality_status": "ok" if data_q.get("ok", True) else "degraded",
        "resources": _resource_usage(),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    patch_platform_state(engine_health=payload)
    return payload
