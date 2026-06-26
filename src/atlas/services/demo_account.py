from __future__ import annotations

from typing import Any

from atlas.brokers.binance import AccountSnapshot, fetch_account_snapshot, fetch_last_price
from atlas.core.models import TradingMode
from atlas.intelligence.dashboard import compute_quick_atlas_score, radar_from_metrics
from atlas.runtime.journal import Journal
from atlas.services.balance_history import load_balance_curve


def demo_snapshot(symbol: str, *, live: bool = False) -> AccountSnapshot | None:
    return fetch_account_snapshot(symbol, live=live)


def journal_entries(*, mode: TradingMode = TradingMode.PAPER) -> list[dict]:
    return Journal(database_url="", mode=mode).to_entries()


def open_entry_from_journal(*, mode: TradingMode, symbol: str) -> dict[str, Any] | None:
    journal = Journal(database_url="", mode=mode)
    open_entry: dict[str, Any] | None = None
    for ev in journal.fetch_events(symbol=symbol, limit=800):
        if ev.get("event") == "entry":
            open_entry = ev
        elif ev.get("event") == "exit":
            open_entry = None
    return open_entry


def entry_price_from_event(ev: dict[str, Any]) -> float | None:
    payload = ev.get("payload") or {}
    fill = payload.get("fill") or {}
    for key in ("filled_price", "entry"):
        val = fill.get(key) if key in fill else payload.get(key)
        if val is not None:
            try:
                px = float(val)
                if px > 0:
                    return px
            except (TypeError, ValueError):
                continue
    return None


def trade_stats(entries: list[dict]) -> dict[str, float | int]:
    if not entries:
        return {"pnl": 0.0, "win_rate": 0.0, "pf": 0.0, "dd": 0.0, "trades": 0, "total_return_pct": 0.0}
    pnls = [float(e.get("pnl", 0)) for e in entries]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0001
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        cumulative += p
        peak = max(peak, cumulative)
        if peak > 0:
            max_dd = max(max_dd, (peak - cumulative) / peak)
    total_pnl = sum(pnls)
    return {
        "pnl": round(total_pnl, 2),
        "win_rate": round(len(wins) / len(pnls) * 100, 1) if pnls else 0.0,
        "pf": round(gross_profit / gross_loss, 2),
        "dd": round(max_dd * 100, 1),
        "trades": len(pnls),
        "total_return_pct": 0.0,
    }


def stats_with_return(entries: list[dict], *, current_balance: float, start_balance: float | None = None) -> dict[str, float | int]:
    stats = trade_stats(entries)
    if start_balance and start_balance > 0:
        stats["total_return_pct"] = round((current_balance / start_balance - 1) * 100, 2)
    elif current_balance > 0 and stats["pnl"]:
        basis = current_balance - float(stats["pnl"])
        if basis > 0:
            stats["total_return_pct"] = round(float(stats["pnl"]) / basis * 100, 2)
    return stats


def build_equity_curve(
    entries: list[dict],
    current_balance: float,
    *,
    mode: TradingMode = TradingMode.PAPER,
) -> list[dict]:
    history = load_balance_curve(mode=mode)
    if len(history) >= 2:
        if history[-1]["equity"] != round(current_balance, 2):
            history = [*history, {"day": "Agora", "equity": round(current_balance, 2)}]
        return history[-60:]

    if current_balance <= 0 and not entries:
        return [{"day": "—", "equity": 0.0}]
    chronological = list(reversed(entries))
    realized = sum(float(e.get("pnl", 0)) for e in chronological)
    start = max(0.0, current_balance - realized)
    points: list[dict] = [{"day": "Início", "equity": round(start, 2)}]
    equity = start
    for i, trade in enumerate(chronological):
        equity += float(trade.get("pnl", 0))
        label = str(trade.get("date") or f"#{i + 1}")[:10]
        points.append({"day": label, "equity": round(equity, 2)})
    if not points or points[-1]["equity"] != round(current_balance, 2):
        points.append({"day": "Agora", "equity": round(current_balance, 2)})
    return points[-60:]


def paper_metrics_for_dashboard(entries: list[dict], current_balance: float) -> dict[str, float | int]:
    stats = stats_with_return(entries, current_balance=current_balance)
    atlas_score = compute_quick_atlas_score(
        drawdown_pct=float(stats["dd"]),
        profit_factor=float(stats["pf"]),
        expectancy=float(stats["pnl"]) / max(int(stats["trades"]), 1),
        sharpe=0.0,
        total_return_pct=float(stats["total_return_pct"]),
        trades=int(stats["trades"]),
    )
    return {
        "win_rate_pct": float(stats["win_rate"]),
        "profit_factor": float(stats["pf"]),
        "max_drawdown_pct": float(stats["dd"]),
        "total_return_pct": float(stats["total_return_pct"]),
        "sharpe": 0.0,
        "atlas_score": atlas_score,
        "trades": int(stats["trades"]),
    }


def radar_from_paper(entries: list[dict], current_balance: float) -> list[dict]:
    metrics = paper_metrics_for_dashboard(entries, current_balance)
    return radar_from_metrics(metrics)


def account_breakdown(snap: AccountSnapshot) -> dict[str, float | str]:
    return {
        "equity_usdt": round(snap.equity_usdt, 2),
        "quote_asset": snap.quote_asset,
        "quote_total": round(snap.quote_total, 2),
        "quote_free": round(snap.quote_free, 2),
        "base_asset": snap.base_asset,
        "base_total": round(snap.base_total, 8),
        "base_free": round(snap.base_free, 8),
    }


def mark_price(symbol: str) -> float:
    return fetch_last_price(symbol)
