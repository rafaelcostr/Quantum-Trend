"""Persistência da camada de plataforma — auditoria e estado operacional."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atlas.core.env import project_root

_STORE_PATH = project_root() / "data" / "runtime" / "platform_state.json"
_MAX_ALERTS = 200
_MAX_DECISIONS = 500
_MAX_STATE_HISTORY = 100


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict[str, Any]:
    return {
        "state": "STOPPED",
        "state_history": [],
        "risk_locked": False,
        "risk_lock_reason": None,
        "risk_lock_at": None,
        "risk_lock_acknowledged": False,
        "recovery": {},
        "data_quality": {},
        "engine_health": {},
        "alerts": [],
        "decisions": [],
        "score_explanations": [],
        "capital_scaling": {"current_risk_pct": None, "history": []},
        "stress_reports": [],
        "trend_exhaustion": {},
        "updated_at": _now(),
    }


def load_platform_state() -> dict[str, Any]:
    if not _STORE_PATH.is_file():
        return _default_state()
    try:
        raw = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        base = _default_state()
        base.update(raw)
        return base
    except (json.JSONDecodeError, OSError):
        return _default_state()


def save_platform_state(data: dict[str, Any]) -> None:
    data["updated_at"] = _now()
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def patch_platform_state(**sections: Any) -> dict[str, Any]:
    data = load_platform_state()
    for key, val in sections.items():
        data[key] = val
    save_platform_state(data)
    return data


def append_alert(alert: dict[str, Any]) -> None:
    data = load_platform_state()
    alerts = list(data.get("alerts") or [])
    alerts.insert(0, alert)
    data["alerts"] = alerts[:_MAX_ALERTS]
    save_platform_state(data)


def append_decision(decision: dict[str, Any]) -> None:
    data = load_platform_state()
    decisions = list(data.get("decisions") or [])
    decisions.insert(0, decision)
    data["decisions"] = decisions[:_MAX_DECISIONS]
    save_platform_state(data)


def append_state_transition(state: str, reason: str, *, meta: dict | None = None) -> None:
    data = load_platform_state()
    data["state"] = state
    history = list(data.get("state_history") or [])
    history.insert(0, {"state": state, "reason": reason, "ts": _now(), "meta": meta or {}})
    data["state_history"] = history[:_MAX_STATE_HISTORY]
    save_platform_state(data)


def set_risk_locked(locked: bool, reason: str | None = None) -> None:
    data = load_platform_state()
    data["risk_locked"] = locked
    data["risk_lock_reason"] = reason
    data["risk_lock_at"] = _now() if locked else None
    if not locked:
        data["risk_lock_acknowledged"] = False
    save_platform_state(data)
    if locked:
        append_state_transition("RISK_LOCKED", reason or "inconsistência detectada")


def acknowledge_risk_lock() -> bool:
    data = load_platform_state()
    if not data.get("risk_locked"):
        return False
    data["risk_lock_acknowledged"] = True
    data["risk_locked"] = False
    data["risk_lock_reason"] = None
    save_platform_state(data)
    append_state_transition("PAPER", "risk lock reconhecido pelo operador")
    return True


def is_risk_locked() -> tuple[bool, str | None]:
    data = load_platform_state()
    if data.get("risk_locked") and not data.get("risk_lock_acknowledged"):
        return True, data.get("risk_lock_reason")
    return False, None
