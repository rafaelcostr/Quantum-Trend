"""Conversao de trades demo para DataFrame (sem dependencia Streamlit)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


def trades_to_dataframe(trades: list[dict[str, Any]]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    rows = []
    for t in trades:
        ts = t.get("timestamp")
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=timezone.utc)
        elif ts:
            dt = pd.Timestamp(ts).to_pydatetime()
        else:
            dt = datetime.now(timezone.utc)
        side = str(t.get("side", "")).lower()
        rows.append(
            {
                "time": dt,
                "side": side,
                "price": float(t.get("price") or 0),
                "amount": float(t.get("amount") or 0),
                "cost": float(t.get("cost") or 0),
                "fee": float(t.get("fee") or 0),
                "symbol": t.get("symbol", ""),
                "id": t.get("id", ""),
            }
        )
    df = pd.DataFrame(rows).sort_values("time")
    if df.empty:
        return df
    signed = df.apply(lambda r: r["cost"] if r["side"] == "buy" else -r["cost"], axis=1)
    df["signed_flow"] = signed
    df["cum_flow"] = signed.cumsum()
    return df
