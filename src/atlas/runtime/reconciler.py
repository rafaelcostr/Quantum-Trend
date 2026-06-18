from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from atlas.core.models import Position, Side
from atlas.runtime.journal import Journal

DUST_QTY = 0.0001


def _parse_ts(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _position_from_entry_event(event: dict[str, Any], symbol: str) -> Position | None:
    payload = event.get("payload") or {}
    fill = payload.get("fill") or {}
    qty = float(fill.get("filled_quantity") or 0)
    if qty <= DUST_QTY:
        return None
    entry_price = float(fill.get("filled_price") or 0)
    metadata = dict(payload.get("metadata") or {})
    metadata["reconciled_from"] = "journal"
    return Position(
        symbol=symbol,
        side=Side.BUY,
        quantity=qty,
        entry_price=entry_price,
        entry_time=_parse_ts(event["ts"]),
        stop_price=payload.get("stop_price"),
        target_price=payload.get("target_price"),
        metadata=metadata,
    )


class PositionReconciler:
    def __init__(self, journal: Journal, broker: Any, symbol: str) -> None:
        self.journal = journal
        self.broker = broker
        self.symbol = symbol

    def _open_entry_from_journal(self) -> dict[str, Any] | None:
        events = self.journal.fetch_events(symbol=self.symbol)
        open_entry: dict[str, Any] | None = None
        for event in events:
            if event.get("symbol") != self.symbol:
                continue
            if event.get("event") == "entry":
                open_entry = event
            elif event.get("event") == "exit":
                open_entry = None
        return open_entry

    def reconcile_on_startup(self) -> tuple[Position | None, dict[str, Any]]:
        meta: dict[str, Any] = {}
        journal_entry = self._open_entry_from_journal()
        journal_pos = _position_from_entry_event(journal_entry, self.symbol) if journal_entry else None
        try:
            broker_pos = self.broker.get_position(self.symbol)
        except Exception as exc:
            broker_pos = None
            meta["broker_error"] = str(exc)

        if journal_pos and broker_pos:
            if broker_pos.quantity <= DUST_QTY:
                meta.update({"source": "journal_mismatch", "warning": "journal_open_but_exchange_flat"})
                return None, meta
            merged = journal_pos.model_copy(update={"quantity": broker_pos.quantity})
            meta["source"] = "journal+broker"
            return merged, meta

        if journal_pos and not broker_pos:
            if meta.get("broker_error"):
                meta["source"] = "journal_only_offline"
                return journal_pos, meta
            meta.update({"source": "journal_mismatch", "warning": "journal_open_but_exchange_flat"})
            return None, meta

        if broker_pos and not journal_pos:
            broker_pos.metadata["reconciled_from"] = "exchange"
            meta.update({"source": "exchange_orphan", "warning": "exchange_balance_without_journal_entry"})
            return broker_pos, meta

        meta["source"] = "flat"
        return None, meta

    def reconcile_periodic(self, current: Position | None) -> tuple[Position | None, dict[str, Any]]:
        meta: dict[str, Any] = {"event": "periodic"}
        try:
            broker_pos = self.broker.get_position(self.symbol)
        except Exception as exc:
            return current, {"broker_error": str(exc)}

        has_broker = broker_pos is not None and broker_pos.quantity > DUST_QTY
        has_engine = current is not None and current.quantity > DUST_QTY

        if has_engine and not has_broker:
            meta["action"] = "cleared_stale_position"
            return None, meta
        if not has_engine and has_broker:
            broker_pos.metadata["reconciled_from"] = "exchange_periodic"
            meta["action"] = "adopted_exchange_position"
            return broker_pos, meta
        if has_engine and has_broker and abs(current.quantity - broker_pos.quantity) > DUST_QTY:
            updated = current.model_copy(update={"quantity": broker_pos.quantity})
            meta["action"] = "qty_synced"
            return updated, meta
        meta["action"] = "ok"
        return current, meta
