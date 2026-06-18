from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from atlas.core.env import project_root
from atlas.core.models import TradingMode


def _path(mode: TradingMode) -> Path:
    base = project_root() / "data" / "runtime"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"balance_{mode.value}.jsonl"


def record_balance(*, mode: TradingMode, equity: float, symbol: str) -> None:
    if equity <= 0:
        return
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "equity": round(equity, 2),
        "symbol": symbol,
    }
    path = _path(mode)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def load_balance_curve(*, mode: TradingMode, limit: int = 500) -> list[dict]:
    path = _path(mode)
    if not path.is_file():
        return []
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if len(rows) > limit:
        rows = rows[-limit:]
    out: list[dict] = []
    for i, row in enumerate(rows):
        ts = str(row.get("ts", ""))
        label = ts[5:10] if len(ts) >= 10 else f"T{i + 1}"
        out.append({"day": label, "equity": float(row.get("equity", 0))})
    return out
