"""Strategy Health Monitor — degradação de performance."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from atlas.core.models import Trade


@dataclass(frozen=True)
class StrategyHealthReport:
    health_score: float
    win_rate_30d: float
    profit_factor_30d: float
    current_drawdown_pct: float
    max_drawdown_pct: float
    expectancy: float
    trades_per_week: float
    stability: str
    total_trades_30d: int


class StrategyHealthMonitor:
    """Calcula saúde da estratégia com base nos trades recentes."""

    def __init__(self, *, lookback_days: int = 30) -> None:
        self.lookback_days = lookback_days

    def evaluate(
        self,
        trades: list[Trade],
        *,
        equity_curve: list[tuple[datetime, float]] | None = None,
    ) -> StrategyHealthReport:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)
        recent = [
            t for t in trades
            if t.is_closed and t.exit_time and _aware(t.exit_time) >= cutoff
        ]
        wins = [t for t in recent if (t.pnl or 0) > 0]
        losses = [t for t in recent if (t.pnl or 0) <= 0]
        gross_profit = sum(t.pnl or 0 for t in wins)
        gross_loss = abs(sum(t.pnl or 0 for t in losses)) or 0.0001
        pf = gross_profit / gross_loss
        win_rate = len(wins) / len(recent) if recent else 0.0
        expectancy = sum(t.pnl or 0 for t in recent) / len(recent) if recent else 0.0
        weeks = max(1.0, self.lookback_days / 7)
        trades_per_week = len(recent) / weeks

        max_dd, current_dd = _drawdowns(equity_curve)
        score = _health_score(win_rate, pf, current_dd, max_dd, len(recent), trades_per_week)
        stability = "estável" if score >= 70 else "atenção" if score >= 50 else "degradada"

        return StrategyHealthReport(
            health_score=round(score, 1),
            win_rate_30d=round(win_rate * 100, 2),
            profit_factor_30d=round(pf, 2),
            current_drawdown_pct=round(current_dd * 100, 2),
            max_drawdown_pct=round(max_dd * 100, 2),
            expectancy=round(expectancy, 2),
            trades_per_week=round(trades_per_week, 2),
            stability=stability,
            total_trades_30d=len(recent),
        )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _drawdowns(curve: list[tuple[datetime, float]] | None) -> tuple[float, float]:
    if not curve:
        return 0.0, 0.0
    peak = curve[0][1]
    max_dd = 0.0
    current_dd = 0.0
    for _, equity in curve:
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
        current_dd = dd
    return max_dd, current_dd


def _health_score(
    win_rate: float,
    pf: float,
    current_dd: float,
    max_dd: float,
    trades: int,
    trades_per_week: float,
) -> float:
    score = 0.0
    score += min(25.0, win_rate * 40)
    score += min(25.0, max(0.0, (pf - 1.0) * 20))
    score += max(0.0, 20.0 - current_dd * 100)
    score += max(0.0, 15.0 - max_dd * 50)
    score += min(10.0, trades / 5)
    score += min(5.0, trades_per_week)
    return min(100.0, score)
