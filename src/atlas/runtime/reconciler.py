from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from atlas.core.log import log_event
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

    def _open_orders(self) -> tuple[list[dict[str, Any]], str | None]:
        fetch = getattr(self.broker, "fetch_open_orders", None)
        if not callable(fetch):
            return [], None
        try:
            orders = fetch(self.symbol) or []
        except Exception as exc:
            return [], str(exc)
        errors = [str(o.get("error")) for o in orders if isinstance(o, dict) and o.get("error")]
        clean = [o for o in orders if isinstance(o, dict) and not o.get("error")]
        return clean, "; ".join(errors) if errors else None

    def _attach_order_meta(self, meta: dict[str, Any]) -> None:
        open_orders, order_error = self._open_orders()
        if order_error:
            meta["open_orders_error"] = order_error[:240]
        if open_orders:
            meta["open_orders_count"] = len(open_orders)
            meta["open_orders"] = open_orders[:5]
            meta["warning"] = meta.get("warning") or "open_orders_without_local_resolution"

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
                self._attach_order_meta(meta)
                self._log_meta("startup", meta)
                return None, meta
            merged = journal_pos.model_copy(update={"quantity": broker_pos.quantity})
            meta["source"] = "journal+broker"
            if abs(journal_pos.quantity - broker_pos.quantity) > DUST_QTY:
                meta["action"] = "qty_synced"
                meta["warning"] = "journal_qty_differs_from_exchange"
            self._attach_order_meta(meta)
            self._log_meta("startup", meta)
            return merged, meta

        if journal_pos and not broker_pos:
            if meta.get("broker_error"):
                meta["source"] = "journal_only_offline"
                self._attach_order_meta(meta)
                self._log_meta("startup", meta)
                return journal_pos, meta
            meta.update({"source": "journal_mismatch", "warning": "journal_open_but_exchange_flat"})
            self._attach_order_meta(meta)
            self._log_meta("startup", meta)
            return None, meta

        if broker_pos and not journal_pos:
            broker_pos.metadata["reconciled_from"] = "exchange"
            meta.update({"source": "exchange_orphan", "warning": "exchange_balance_without_journal_entry"})
            self._attach_order_meta(meta)
            self._log_meta("startup", meta)
            return broker_pos, meta

        meta["source"] = "flat"
        self._attach_order_meta(meta)
        if meta.get("open_orders_count"):
            meta["action"] = "open_orders_detected_while_flat"
        self._log_meta("startup", meta)
        return None, meta

    def _log_meta(self, phase: str, meta: dict[str, Any]) -> None:
        log_event(
            30 if meta.get("warning") or meta.get("broker_error") or meta.get("open_orders_count") else 20,
            "reconciler.checked",
            module="runtime.reconciler",
            phase=phase,
            symbol=self.symbol,
            source=meta.get("source"),
            action=meta.get("action"),
            warning=meta.get("warning"),
            open_orders_count=meta.get("open_orders_count"),
            broker_error=meta.get("broker_error"),
        )

    def reconcile_periodic(self, current: Position | None) -> tuple[Position | None, dict[str, Any]]:
        meta: dict[str, Any] = {"event": "periodic"}
        try:
            broker_pos = self.broker.get_position(self.symbol)
        except Exception as exc:
            meta = {"broker_error": str(exc)}
            self._attach_order_meta(meta)
            self._log_meta("periodic", meta)
            return current, meta

        has_broker = broker_pos is not None and broker_pos.quantity > DUST_QTY
        has_engine = current is not None and current.quantity > DUST_QTY

        if has_engine and not has_broker:
            meta["action"] = "cleared_stale_position"
            meta["warning"] = "engine_position_without_exchange_position"
            self._attach_order_meta(meta)
            self._log_meta("periodic", meta)
            return None, meta
        if not has_engine and has_broker:
            broker_pos.metadata["reconciled_from"] = "exchange_periodic"
            meta["action"] = "adopted_exchange_position"
            meta["warning"] = "exchange_position_without_engine_position"
            self._attach_order_meta(meta)
            self._log_meta("periodic", meta)
            return broker_pos, meta
        if has_engine and has_broker and abs(current.quantity - broker_pos.quantity) > DUST_QTY:
            updated = current.model_copy(update={"quantity": broker_pos.quantity})
            meta["action"] = "qty_synced"
            meta["warning"] = "engine_qty_differs_from_exchange"
            self._attach_order_meta(meta)
            self._log_meta("periodic", meta)
            return updated, meta
        self._attach_order_meta(meta)
        if meta.get("open_orders_count"):
            meta["action"] = "open_orders_detected"
            self._log_meta("periodic", meta)
            return current, meta
        meta["action"] = "ok"
        self._log_meta("periodic", meta)
        return current, meta
