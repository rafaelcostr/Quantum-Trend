from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TradeMarker:
    time: datetime
    price: float
    side: str
    label: str


@dataclass
class PerformanceSnapshot:
    initial_capital: float
    current_equity: float
    net_pnl: float
    net_pnl_pct: float
    max_drawdown_pct: float
    peak_equity: float
    trade_count: int
    equity_curve: list[dict[str, Any]]


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_trade_markers(events: list[dict[str, Any]]) -> list[TradeMarker]:
    markers: list[TradeMarker] = []
    chronological = sorted(events, key=lambda e: _parse_ts(e.get("ts")) or datetime.min)
    for ev in chronological:
        event = ev.get("event")
        if event not in {"entry", "exit"}:
            continue
        payload = ev.get("payload") or {}
        fill = payload.get("fill") or {}
        price = float(fill.get("filled_price") or 0)
        if price <= 0:
            continue
        ts = _parse_ts(ev.get("ts"))
        if ts is None:
            continue
        side = "buy" if event == "entry" else "sell"
        reason = str(payload.get("signal") or event)
        markers.append(TradeMarker(time=ts, price=price, side=side, label=reason))
    return markers


def compute_performance(
    events: list[dict[str, Any]],
    initial_capital: float,
    current_equity: float | None = None,
) -> PerformanceSnapshot:
    chronological = sorted(events, key=lambda e: _parse_ts(e.get("ts")) or datetime.min)

    curve: list[dict[str, Any]] = []
    peak = initial_capital
    max_dd = 0.0
    trade_count = sum(1 for e in chronological if e.get("event") in {"entry", "exit"})

    for ev in chronological:
        payload = ev.get("payload") or {}
        equity = payload.get("equity")
        if equity is None:
            continue
        equity = float(equity)
        ts = _parse_ts(ev.get("ts"))
        if ts is None:
            continue
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
        curve.append({"ts": ts, "equity": equity})

    if current_equity is not None:
        if not curve or curve[-1]["equity"] != current_equity:
            now = datetime.now().astimezone()
            peak = max(peak, current_equity)
            dd = (peak - current_equity) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
            curve.append({"ts": now, "equity": current_equity})

    final_equity = current_equity if current_equity is not None else (curve[-1]["equity"] if curve else initial_capital)
    net_pnl = final_equity - initial_capital
    net_pnl_pct = net_pnl / initial_capital if initial_capital else 0.0

    return PerformanceSnapshot(
        initial_capital=initial_capital,
        current_equity=final_equity,
        net_pnl=net_pnl,
        net_pnl_pct=net_pnl_pct,
        max_drawdown_pct=max_dd,
        peak_equity=peak,
        trade_count=trade_count,
        equity_curve=curve,
    )
