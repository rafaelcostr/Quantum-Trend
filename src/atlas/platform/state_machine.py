"""State Machine — estados operacionais explícitos."""
from __future__ import annotations

from typing import Any

from atlas.core.models import TradingMode
from atlas.platform.models import PlatformState
from atlas.platform.store import append_state_transition, load_platform_state, patch_platform_state
from atlas.runtime.state import bot_state

_VALID_TRANSITIONS: dict[PlatformState, set[PlatformState]] = {
    PlatformState.STOPPED: {PlatformState.SYNCING, PlatformState.BACKTESTING, PlatformState.ERROR},
    PlatformState.SYNCING: {PlatformState.ANALYZING, PlatformState.PAPER, PlatformState.LIVE, PlatformState.RISK_LOCKED, PlatformState.ERROR},
    PlatformState.ANALYZING: {PlatformState.PAPER, PlatformState.LIVE, PlatformState.COOLDOWN, PlatformState.RISK_LOCKED, PlatformState.STOPPED, PlatformState.ERROR},
    PlatformState.BACKTESTING: {PlatformState.STOPPED, PlatformState.ANALYZING, PlatformState.ERROR},
    PlatformState.PAPER: {PlatformState.ANALYZING, PlatformState.WAITING_APPROVAL, PlatformState.COOLDOWN, PlatformState.RISK_LOCKED, PlatformState.STOPPED, PlatformState.ERROR},
    PlatformState.WAITING_APPROVAL: {PlatformState.LIVE, PlatformState.PAPER, PlatformState.STOPPED, PlatformState.RISK_LOCKED},
    PlatformState.LIVE: {PlatformState.COOLDOWN, PlatformState.RISK_LOCKED, PlatformState.STOPPED, PlatformState.ERROR},
    PlatformState.COOLDOWN: {PlatformState.ANALYZING, PlatformState.PAPER, PlatformState.STOPPED, PlatformState.RISK_LOCKED},
    PlatformState.RISK_LOCKED: {PlatformState.SYNCING, PlatformState.STOPPED, PlatformState.PAPER, PlatformState.LIVE},
    PlatformState.ERROR: {PlatformState.STOPPED, PlatformState.SYNCING},
}

_ALLOWED_EVENTS: dict[PlatformState, set[str]] = {
    PlatformState.STOPPED: {"start", "backtest", "view"},
    PlatformState.SYNCING: {"view"},
    PlatformState.ANALYZING: {"tick", "view"},
    PlatformState.BACKTESTING: {"view", "cancel_backtest"},
    PlatformState.PAPER: {"tick", "stop", "view", "trade"},
    PlatformState.WAITING_APPROVAL: {"view", "approve_live", "reject"},
    PlatformState.LIVE: {"tick", "stop", "view", "trade"},
    PlatformState.COOLDOWN: {"view"},
    PlatformState.RISK_LOCKED: {"view", "acknowledge", "stop"},
    PlatformState.ERROR: {"view", "stop", "recover"},
}

_FORBIDDEN_EVENTS: dict[PlatformState, set[str]] = {
    PlatformState.RISK_LOCKED: {"trade", "start"},
    PlatformState.STOPPED: {"trade", "tick"},
    PlatformState.SYNCING: {"trade", "start"},
    PlatformState.COOLDOWN: {"trade"},
    PlatformState.ERROR: {"trade", "start"},
}


def current_state() -> PlatformState:
    raw = load_platform_state().get("state") or PlatformState.STOPPED.value
    try:
        return PlatformState(str(raw))
    except ValueError:
        return PlatformState.STOPPED


def transition(to: PlatformState, reason: str, *, force: bool = False, meta: dict | None = None) -> PlatformState:
    current = current_state()
    if not force and to not in _VALID_TRANSITIONS.get(current, set()) and current != to:
        append_state_transition(current.value, f"transição rejeitada → {to.value}: {reason}", meta={"rejected": True, **(meta or {})})
        return current
    append_state_transition(to.value, reason, meta=meta)
    return to


def sync_state_from_runtime(*, backtesting: bool = False) -> PlatformState:
    if load_platform_state().get("risk_locked") and not load_platform_state().get("risk_lock_acknowledged"):
        return transition(PlatformState.RISK_LOCKED, "risk lock ativo", force=True)

    if backtesting:
        return transition(PlatformState.BACKTESTING, "backtest em execução", force=True)

    snap = bot_state.snapshot()
    if not snap.get("running"):
        return transition(PlatformState.STOPPED, "bot parado", force=True)

    mode = bot_state.mode
    if mode == TradingMode.LIVE:
        return transition(PlatformState.LIVE, "modo live", force=True)

    from atlas.runtime.risk_store import is_trading_paused

    paused, _ = is_trading_paused()
    if paused:
        return transition(PlatformState.COOLDOWN, "cooldown operacional", force=True)

    if snap.get("in_position"):
        return transition(PlatformState.PAPER, "paper com posição", force=True)

    return transition(PlatformState.ANALYZING, "paper analisando", force=True)


def can_execute_event(event: str) -> bool:
    state = current_state()
    if event in _FORBIDDEN_EVENTS.get(state, set()):
        return False
    allowed = _ALLOWED_EVENTS.get(state, set())
    return event in allowed or event == "view"


def state_machine_payload() -> dict[str, Any]:
    data = load_platform_state()
    state = current_state()
    return {
        "current": state.value,
        "history": data.get("state_history") or [],
        "allowed_events": sorted(_ALLOWED_EVENTS.get(state, set())),
        "forbidden_events": sorted(_FORBIDDEN_EVENTS.get(state, set())),
        "can_trade": can_execute_event("trade"),
    }
