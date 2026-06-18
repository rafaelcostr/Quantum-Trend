from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from atlas.core.models import TradingMode
from atlas.runtime.journal import Journal
from atlas.runtime.state import active_config, bot_state


def _format_message(event: str, payload: dict[str, Any]) -> str:
    if event == "runner_start":
        tf = payload.get("timeframe", "")
        slot = payload.get("slot", "")
        suffix = f" · {tf.upper()}" if tf else ""
        slot_note = f" [{slot}]" if slot else ""
        return f"Engine iniciado · {payload.get('strategy', '?')}{suffix}{slot_note} · modo {payload.get('mode', '?')}"
    if event == "entry":
        fill = payload.get("fill") or {}
        px = fill.get("filled_price") or payload.get("entry")
        return f"ENTRADA · ${float(px or 0):,.2f} · {payload.get('signal', '')}"
    if event == "exit":
        fill = payload.get("fill") or {}
        px = fill.get("filled_price") or payload.get("exit")
        return f"SAÍDA · ${float(px or 0):,.2f} · {payload.get('signal', '')}"
    if event == "tick":
        signal = payload.get("signal", "HOLD")
        reason = payload.get("reason", "")
        action = payload.get("action")
        if action == "entry":
            return f"🟢 Execução entrada · {reason}"
        if action == "exit":
            return f"🔴 Execução saída · {reason}"
        if action == "blocked":
            return f"Bloqueado · {payload.get('block_reason', reason)}"
        if payload.get("status") == "warming_up":
            return f"Aquecendo · {payload.get('candles', 0)} candles"
        return f"Sinal {signal} · {reason}"
    if event == "error":
        return f"Erro · {payload.get('error', '?')}"
    if event == "reconcile":
        return f"Reconciliação · {payload.get('action', payload.get('source', 'ok'))}"
    return event


def get_operations_feed(*, limit: int = 100) -> dict[str, Any]:
    mode = bot_state.mode if bot_state.running else TradingMode.PAPER
    journal = Journal(database_url="", mode=mode)
    raw = journal.fetch_events(limit=max(limit, 200))
    items: list[dict[str, Any]] = []

    for ev in reversed(raw[-limit:]):
        payload = ev.get("payload") or {}
        event = str(ev.get("event") or "event")
        items.append(
            {
                "ts": ev.get("ts"),
                "event": event,
                "symbol": ev.get("symbol"),
                "signal": payload.get("signal"),
                "reason": payload.get("reason"),
                "action": payload.get("action"),
                "equity": payload.get("equity"),
                "status": payload.get("status"),
                "message": _format_message(event, payload),
            }
        )

    snap = bot_state.snapshot()
    cfg = active_config()
    poll = cfg.runtime.poll_seconds if bot_state.running else None
    next_tick_in: int | None = None
    if bot_state.running and snap.get("last_tick_at") and poll:
        last = datetime.fromisoformat(str(snap["last_tick_at"]).replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        next_tick_in = max(0, int(poll - elapsed))

    return {
        "items": items,
        "bot": snap,
        "mode": mode.value,
        "poll_seconds": poll,
        "next_tick_in": next_tick_in,
    }
