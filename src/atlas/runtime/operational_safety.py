from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from atlas.core.env import project_root
from atlas.core.models import Order, SignalAction
from atlas.core.symbols import base_from_symbol

_PATH = project_root() / "data" / "runtime" / "operational_safety.json"
_ORDER_TTL_SECONDS = 60 * 60 * 24


@dataclass(frozen=True)
class KillSwitchDecision:
    blocked: bool
    reason: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict[str, Any]:
    if not _PATH.is_file():
        return {}
    try:
        return json.loads(_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict[str, Any]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _scoped_switches(data: dict[str, Any]) -> dict[str, Any]:
    switches = data.setdefault("kill_switches", {})
    switches.setdefault("assets", {})
    switches.setdefault("strategies", {})
    return switches


def set_scoped_kill_switch(
    *,
    scope: str,
    key: str,
    active: bool,
    reason: str = "",
) -> dict[str, Any]:
    data = _load()
    switches = _scoped_switches(data)
    bucket = "assets" if scope == "asset" else "strategies" if scope == "strategy" else None
    if bucket is None:
        raise ValueError("scope deve ser asset ou strategy")
    normalized = key.upper() if bucket == "assets" else key
    if active:
        switches[bucket][normalized] = {
            "active": True,
            "reason": reason or "manual",
            "updated_at": _now_iso(),
        }
    else:
        switches[bucket].pop(normalized, None)
    _save(data)
    return switches


def kill_switch_snapshot() -> dict[str, Any]:
    return _scoped_switches(_load())


def evaluate_scoped_kill_switch(
    *,
    global_active: bool,
    symbol: str,
    strategy: str,
) -> KillSwitchDecision:
    if global_active:
        return KillSwitchDecision(True, "Kill switch global ativo")
    switches = kill_switch_snapshot()
    base = base_from_symbol(symbol).upper()
    asset = switches.get("assets", {}).get(base)
    if asset and asset.get("active"):
        return KillSwitchDecision(True, f"Kill switch do ativo {base}: {asset.get('reason') or 'manual'}")
    strategy_switch = switches.get("strategies", {}).get(strategy)
    if strategy_switch and strategy_switch.get("active"):
        return KillSwitchDecision(
            True,
            f"Kill switch da estratégia {strategy}: {strategy_switch.get('reason') or 'manual'}",
        )
    return KillSwitchDecision(False)


def assert_no_conflicting_configs(configs: list[tuple[str, Any]]) -> None:
    seen_slot: set[str] = set()
    seen_tuple: dict[tuple[str, str, str], str] = {}
    for key, cfg in configs:
        if key in seen_slot:
            raise RuntimeError(f"Slot duplicado: {key}")
        seen_slot.add(key)
        marker = (
            str(cfg.exchange.symbol).upper(),
            str(cfg.exchange.timeframe).lower(),
            str(cfg.strategy.name),
        )
        if marker in seen_tuple:
            raise RuntimeError(
                "Bot conflitante: mesmo símbolo/timeframe/estratégia "
                f"({marker[0]} · {marker[1]} · {marker[2]}) em {seen_tuple[marker]} e {key}"
            )
        seen_tuple[marker] = key


def decision_id(
    *,
    mode: str,
    symbol: str,
    timeframe: str,
    strategy: str,
    action: SignalAction,
    candle_ts: Any,
    slot: str = "",
) -> str:
    raw = "|".join(
        [
            mode,
            symbol.upper(),
            timeframe.lower(),
            strategy,
            action.value,
            str(candle_ts),
            slot,
        ]
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:18]
    return f"qt-{digest}"


def _orders(data: dict[str, Any]) -> dict[str, Any]:
    orders = data.setdefault("orders", {})
    cutoff = time.time() - _ORDER_TTL_SECONDS
    for key, item in list(orders.items()):
        try:
            if float(item.get("created_epoch", 0)) < cutoff:
                orders.pop(key, None)
        except (TypeError, ValueError):
            orders.pop(key, None)
    return orders


def begin_order_decision(decision: str, *, context: dict[str, Any]) -> tuple[bool, dict[str, Any] | None]:
    data = _load()
    orders = _orders(data)
    existing = orders.get(decision)
    if existing and existing.get("status") in {"pending", "submitted", "success"}:
        return False, existing
    orders[decision] = {
        "decision_id": decision,
        "status": "pending",
        "context": context,
        "created_at": _now_iso(),
        "created_epoch": time.time(),
        "updated_at": _now_iso(),
    }
    _save(data)
    return True, None


def finish_order_decision(decision: str, *, status: str, result: dict[str, Any] | None = None) -> None:
    data = _load()
    orders = _orders(data)
    item = orders.setdefault(
        decision,
        {"decision_id": decision, "created_at": _now_iso(), "created_epoch": time.time()},
    )
    item["status"] = status
    item["result"] = result or {}
    item["updated_at"] = _now_iso()
    _save(data)


def attach_client_order_id(order: Order, decision: str) -> Order:
    if order.client_order_id:
        return order
    return order.model_copy(update={"client_order_id": decision[:32]})
