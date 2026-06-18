"""Compatibilidade dashboard — score simplificado e radar."""
from __future__ import annotations


def compute_quick_atlas_score(
    *,
    drawdown_pct: float,
    profit_factor: float,
    expectancy: float,
    sharpe: float,
    total_return_pct: float,
    trades: int,
) -> float:
    def clamp(v: float, lo: float = 0, hi: float = 100) -> float:
        return max(lo, min(hi, v))

    score = (
        clamp(100 - drawdown_pct * 2.5) * 0.25
        + clamp(profit_factor * 35) * 0.25
        + clamp(50 + expectancy * 10) * 0.15
        + clamp(sharpe * 25 + 50) * 0.15
        + clamp(50 + total_return_pct) * 0.10
        + clamp(trades * 2) * 0.05
        + 5
    )
    return round(clamp(score), 1)


def radar_from_metrics(metrics: dict) -> list[dict]:
    dd = float(metrics.get("max_drawdown_pct", 10))
    pf = float(metrics.get("profit_factor", 1))
    wr = float(metrics.get("win_rate_pct", 50))
    ret = float(metrics.get("total_return_pct", 0))
    sharpe = float(metrics.get("sharpe", 0))
    return [
        {"axis": "Rentabilidade", "v": int(min(100, max(0, 50 + ret)))},
        {"axis": "Drawdown", "v": int(min(100, max(0, 100 - dd * 2)))},
        {"axis": "Consistência", "v": int(min(100, max(0, wr)))},
        {"axis": "Estabilidade", "v": int(min(100, max(0, 50 + sharpe * 15)))},
        {"axis": "Controle de Risco", "v": int(min(100, max(0, 100 - dd * 1.5)))},
    ]


def strategy_status(score: float, pf: float, dd: float) -> str:
    if score >= 75 and pf >= 1.5 and dd <= 12:
        return "Aprovada"
    if score >= 60:
        return "Demo"
    if pf < 1.0 or dd > 20:
        return "Reprovada"
    return "Backtest"
