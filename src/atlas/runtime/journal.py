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
