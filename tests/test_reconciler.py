from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from atlas.core.models import Position, Side, TradingMode
from atlas.runtime.journal import Journal
from atlas.runtime.reconciler import PositionReconciler


class StubBroker:
    def __init__(self, qty: float = 0.0) -> None:
        self.qty = qty

    def get_position(self, symbol: str) -> Position | None:
        if self.qty <= 0.0001:
            return None
        return Position(
            symbol=symbol,
            side=Side.BUY,
            quantity=self.qty,
            entry_price=0.0,
            entry_time=datetime.now(timezone.utc),
        )


def _journal_with_events(tmp_path: Path, events: list[dict]) -> Journal:
    journal = Journal("postgresql://invalid:5432/nodb", TradingMode.PAPER, fallback_dir=tmp_path)
    assert journal.using_file_fallback
    for event in events:
        journal.log(event["event"], "BTC/USDT", **event.get("payload", {}))
    return journal


def test_reconcile_from_journal_and_broker(tmp_path):
    journal = _journal_with_events(
        tmp_path,
        [
            {
                "event": "entry",
                "payload": {
                    "fill": {"filled_quantity": 0.05, "filled_price": 60000.0},
                    "metadata": {"regime": "bull"},
                    "stop_price": 58000.0,
                },
            }
        ],
    )
    reconciler = PositionReconciler(journal, StubBroker(qty=0.05), "BTC/USDT")
    pos, meta = reconciler.reconcile_on_startup()
    assert pos is not None
    assert pos.quantity == 0.05
    assert pos.entry_price == 60000.0
    assert meta["source"] == "journal+broker"


def test_reconcile_journal_closed_by_exit(tmp_path):
    journal = _journal_with_events(
        tmp_path,
        [
            {"event": "entry", "payload": {"fill": {"filled_quantity": 0.05, "filled_price": 60000.0}}},
            {"event": "exit", "payload": {"signal": "bearish cross"}},
        ],
    )
    reconciler = PositionReconciler(journal, StubBroker(qty=0.0), "BTC/USDT")
    pos, meta = reconciler.reconcile_on_startup()
    assert pos is None
    assert meta["source"] == "flat"


def test_reconcile_orphan_exchange_balance(tmp_path):
    journal = Journal("postgresql://invalid:5432/nodb", TradingMode.PAPER, fallback_dir=tmp_path)
    reconciler = PositionReconciler(journal, StubBroker(qty=0.02), "BTC/USDT")
    pos, meta = reconciler.reconcile_on_startup()
    assert pos is not None
    assert pos.quantity == 0.02
    assert meta["source"] == "exchange_orphan"


def test_reconcile_trust_journal_when_broker_offline(tmp_path):
    journal = _journal_with_events(
        tmp_path,
        [
            {
                "event": "entry",
                "payload": {"fill": {"filled_quantity": 0.03, "filled_price": 55000.0}},
            }
        ],
    )

    class FailingBroker:
        def get_position(self, symbol: str) -> Position | None:
            raise ConnectionError("offline")

    reconciler = PositionReconciler(journal, FailingBroker(), "BTC/USDT")
    pos, meta = reconciler.reconcile_on_startup()
    assert pos is not None
    assert pos.quantity == 0.03
    assert meta["source"] == "journal_only_offline"


def test_reconcile_periodic_clears_stale_position(tmp_path):
    journal = Journal("postgresql://invalid:5432/nodb", TradingMode.PAPER, fallback_dir=tmp_path)
    current = Position(
        symbol="BTC/USDT",
        side=Side.BUY,
        quantity=0.01,
        entry_price=50000,
        entry_time=datetime.now(timezone.utc),
    )
    reconciler = PositionReconciler(journal, StubBroker(qty=0.0), "BTC/USDT")
    pos, meta = reconciler.reconcile_periodic(current)
    assert pos is None
    assert meta["action"] == "cleared_stale_position"
