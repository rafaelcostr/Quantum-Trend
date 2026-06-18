"""Estatísticas de backtest por módulo de entrada."""
from __future__ import annotations

from atlas.core.models import Trade
from atlas.quantum.health import StrategyHealthMonitor
from atlas.quantum.models import EntryModule


def _module_from_trade(trade: Trade) -> str | None:
    meta = trade.metadata or {}
    raw = meta.get("entry_module")
    if raw:
        return str(raw)
    reason = str(meta.get("reason") or "")
    for mod in EntryModule:
        if mod == EntryModule.AUTO:
            continue
        if mod.value in reason.lower():
            return mod.value
    return None


def compute_module_backtest_stats(trades: list[Trade]) -> dict[str, dict[str, float | int]]:
    """Métricas por módulo: trades, win rate, PF, drawdown proxy."""
    grouped: dict[str, list[Trade]] = {m.value: [] for m in EntryModule if m != EntryModule.AUTO}
    for trade in trades:
        if not trade.is_closed:
            continue
        mod = _module_from_trade(trade)
        if mod and mod in grouped:
            grouped[mod].append(trade)

    monitor = StrategyHealthMonitor()
    out: dict[str, dict[str, float | int]] = {}
    for mod, mod_trades in grouped.items():
        if not mod_trades:
            out[mod] = {
                "trades": 0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "health_score": 0.0,
            }
            continue
        wins = [t for t in mod_trades if (t.pnl or 0) > 0]
        losses = [t for t in mod_trades if (t.pnl or 0) <= 0]
        gross_profit = sum(t.pnl or 0 for t in wins)
        gross_loss = abs(sum(t.pnl or 0 for t in losses)) or 0.0001
        pf = gross_profit / gross_loss
        win_rate = len(wins) / len(mod_trades) * 100
        health = monitor.evaluate(mod_trades)
        out[mod] = {
            "trades": len(mod_trades),
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": round(pf, 2),
            "max_drawdown_pct": health.max_drawdown_pct,
            "health_score": health.health_score,
        }
    return out
