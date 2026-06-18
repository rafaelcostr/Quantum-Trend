from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atlas.core.env import project_root
from atlas.core.models import TradingMode


class Journal:
    """Append-only audit log — arquivo JSONL (sem PostgreSQL obrigatório)."""

    def __init__(
        self,
        database_url: str | None = None,
        mode: TradingMode | None = None,
        fallback_dir: Path | None = None,
    ) -> None:
        self.database_url = database_url or ""
        self.mode = mode or TradingMode.PAPER
        base = fallback_dir or project_root() / "data" / "journal"
        base.mkdir(parents=True, exist_ok=True)
        self._file_path = base / f"{self.mode.value}.jsonl"

    @property
    def using_file_fallback(self) -> bool:
        return True

    def log(self, event: str, symbol: str | None = None, **payload: Any) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": self.mode.value,
            "event": event,
            "symbol": symbol,
            "payload": payload,
        }
        with self._file_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")

    def fetch_events(self, *, symbol: str | None = None, limit: int = 2000) -> list[dict[str, Any]]:
        if not self._file_path.is_file():
            return []
        events: list[dict[str, Any]] = []
        with self._file_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("mode") != self.mode.value:
                    continue
                if symbol is not None and record.get("symbol") != symbol:
                    continue
                events.append(
                    {
                        "ts": record.get("ts"),
                        "event": record.get("event"),
                        "symbol": record.get("symbol"),
                        "payload": record.get("payload") or {},
                    }
                )
        if len(events) > limit:
            events = events[-limit:]
        return events

    def append(self, entry: dict[str, Any]) -> None:
        event = "trade_open" if entry.get("type") == "trade_open" else "trade_close"
        self.log(event, entry.get("asset"), **entry)

    def to_entries(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        open_trade: dict[str, Any] | None = None
        for ev in self.fetch_events(limit=5000):
            payload = ev.get("payload") or {}
            if ev.get("event") == "entry" or payload.get("type") == "trade_open":
                open_trade = {
                    "date": payload.get("date") or str(ev.get("ts", ""))[:16],
                    "asset": payload.get("asset") or ev.get("symbol") or "BTC/USDT",
                    "entry": float(payload.get("entry") or payload.get("fill", {}).get("filled_price") or 0),
                    "exit": 0.0,
                    "pnl": 0.0,
                    "strategy": payload.get("strategy") or "",
                    "side": "LONG",
                }
            elif ev.get("event") == "exit" or payload.get("type") == "trade_close":
                if open_trade:
                    open_trade["exit"] = float(payload.get("exit") or payload.get("fill", {}).get("filled_price") or 0)
                    open_trade["pnl"] = float(payload.get("pnl") or 0)
                    out.append(open_trade)
                    open_trade = None
        return list(reversed(out[-100:]))
