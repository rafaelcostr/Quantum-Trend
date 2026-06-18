"""Estado em tempo real do QuantumTrend Pro (scores, fase do bot)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atlas.core.env import project_root

_STORE_PATH = project_root() / "data" / "runtime" / "quantum_state.json"


def _load() -> dict[str, Any]:
    if not _STORE_PATH.is_file():
        return {}
    try:
        return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict[str, Any]) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def update_runtime_snapshot(
    *,
    alignment_score: float | None = None,
    alignment_breakdown: dict[str, float] | None = None,
    health_score: float | None = None,
    regime: str | None = None,
    regime_label: str | None = None,
    bot_phase: str | None = None,
    last_signal: str | None = None,
    last_reason: str | None = None,
    strategy: str | None = None,
    entry_module: str | None = None,
    entry_confidence: float | None = None,
    entry_result: str | None = None,
    module_status: dict[str, object] | None = None,
    module_health: dict[str, float] | None = None,
    rejected_modules: list[dict[str, object]] | None = None,
) -> dict[str, Any]:
    data = _load()
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if alignment_score is not None:
        data["alignment_score"] = round(float(alignment_score), 1)
        history = list(data.get("alignment_history") or [])
        history.append({"ts": data["updated_at"], "score": data["alignment_score"]})
        data["alignment_history"] = history[-500:]
    if alignment_breakdown is not None:
        data["alignment_breakdown"] = alignment_breakdown
    if health_score is not None:
        data["health_score"] = round(float(health_score), 1)
        health_hist = list(data.get("health_history") or [])
        health_hist.append({"ts": data["updated_at"], "score": data["health_score"]})
        data["health_history"] = health_hist[-500:]
    if regime is not None:
        data["regime"] = regime
    if regime_label is not None:
        data["regime_label"] = regime_label
    if bot_phase is not None:
        data["bot_phase"] = bot_phase
    if last_signal is not None:
        data["last_signal"] = last_signal
    if last_reason is not None:
        data["last_reason"] = last_reason
    if strategy is not None:
        data["strategy"] = strategy
    if entry_module is not None:
        data["entry_module"] = entry_module
    if entry_confidence is not None:
        data["entry_confidence"] = round(float(entry_confidence), 1)
    if entry_result is not None:
        data["entry_result"] = entry_result
    if module_status is not None:
        data["module_status"] = module_status
    if module_health is not None:
        data["module_health"] = module_health
    if rejected_modules is not None:
        data["rejected_modules"] = rejected_modules
    _save(data)
    return data


def get_runtime_snapshot() -> dict[str, Any]:
    return _load()
