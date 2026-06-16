from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from atlas.core.models import TradingMode


class Journal:
    """Append-only audit log for backtest, paper, and live."""

    def __init__(
        self,
        database_url: str,
        mode: TradingMode,
        fallback_dir: Path | None = None,
    ) -> None:
        self.database_url = database_url
        self.mode = mode
        self._engine = None
        self._file_path: Path | None = None
        self._db_error: str | None = None

        try:
            engine = create_engine(database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self._engine = engine
        except Exception as exc:
            self._db_error = str(exc)
            base = fallback_dir or Path("data/journal")
            base.mkdir(parents=True, exist_ok=True)
            self._file_path = base / f"{mode.value}.jsonl"

    @property
    def using_file_fallback(self) -> bool:
        return self._engine is None

    @property
    def fallback_message(self) -> str | None:
        if not self.using_file_fallback:
            return None
        return (
            f"PostgreSQL unavailable ({self._db_error}). "
            f"Logging to {self._file_path}. "
            "Start DB with: docker compose up -d"
        )

    def log(self, event: str, symbol: str | None = None, **payload: Any) -> None:
        ts = datetime.now(timezone.utc)
        record = {
            "ts": ts.isoformat(),
            "mode": self.mode.value,
            "event": event,
            "symbol": symbol,
            "payload": payload,
        }

        if self._engine is not None:
            try:
                with self._engine.begin() as conn:
                    conn.execute(
                        text(
                            """
                            INSERT INTO journal (ts, mode, event, symbol, payload)
                            VALUES (:ts, :mode, :event, :symbol, CAST(:payload AS jsonb))
                            """
                        ),
                        {
                            "ts": ts,
                            "mode": self.mode.value,
                            "event": event,
                            "symbol": symbol,
                            "payload": json.dumps(payload),
                        },
                    )
                return
            except Exception as exc:
                if self._file_path is None:
                    base = Path("data/journal")
                    base.mkdir(parents=True, exist_ok=True)
                    self._file_path = base / f"{self.mode.value}.jsonl"
                self._db_error = str(exc)

        if self._file_path is not None:
            with self._file_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")

    def fetch_events(
        self,
        *,
        symbol: str | None = None,
        limit: int = 2000,
    ) -> list[dict[str, Any]]:
        """Return journal events oldest-first for this mode."""
        if self._engine is not None:
            try:
                with self._engine.connect() as conn:
                    rows = conn.execute(
                        text(
                            """
                            SELECT ts, event, symbol, payload
                            FROM journal
                            WHERE mode = :mode
                              AND (:symbol IS NULL OR symbol = :symbol)
                            ORDER BY ts ASC
                            LIMIT :limit
                            """
                        ),
                        {"mode": self.mode.value, "symbol": symbol, "limit": limit},
                    ).mappings()
                    return [
                        {
                            "ts": row["ts"].isoformat()
                            if hasattr(row["ts"], "isoformat")
                            else str(row["ts"]),
                            "event": row["event"],
                            "symbol": row["symbol"],
                            "payload": row["payload"] or {},
                        }
                        for row in rows
                    ]
            except Exception:
                pass

        if self._file_path is None or not self._file_path.is_file():
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
