"""Auto Capital Scaling — risco dinâmico baseado em health scores."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from atlas.platform.store import load_platform_state, save_platform_state
from atlas.runtime.risk_store import get_risk_settings, update_risk_settings


def _combined_health(*, strategy_health: float, engine_health: float, data_health: float) -> float:
    weights = (0.4, 0.3, 0.3)
    return round(strategy_health * weights[0] + engine_health * weights[1] + data_health * weights[2], 1)


def risk_pct_for_health(health: float) -> float | None:
    if health >= 95:
        return 1.0
    if health >= 80:
        return 0.75
    if health >= 60:
        return 0.50
    if health >= 40:
        return 0.25
    return None


def apply_capital_scaling(
    *,
    strategy_health: float,
    engine_health: float,
    data_health: float,
) -> dict[str, Any]:
    combined = _combined_health(
        strategy_health=strategy_health,
        engine_health=engine_health,
        data_health=data_health,
    )
    target = risk_pct_for_health(combined)
    current = get_risk_settings()

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "combined_health": combined,
        "strategy_health": strategy_health,
        "engine_health": engine_health,
        "data_health": data_health,
        "target_risk_pct": target,
        "previous_risk_pct": current.risk_per_trade_pct,
        "paused": target is None,
    }

    data = load_platform_state()
    history = list((data.get("capital_scaling") or {}).get("history") or [])
    history.insert(0, entry)

    if target is None:
        entry["action"] = "pause"
        save_platform_state({**data, "capital_scaling": {"current_risk_pct": 0, "paused": True, "history": history[:100]}})
        return entry

    if abs(current.risk_per_trade_pct - target) > 0.01:
        update_risk_settings(risk_per_trade_pct=target)
        entry["action"] = "adjusted"

    save_platform_state(
        {
            **data,
            "capital_scaling": {
                "current_risk_pct": target,
                "paused": False,
                "combined_health": combined,
                "history": history[:100],
            },
        }
    )
    return entry
