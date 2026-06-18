"""Portfolio Manager — visão consolidada de capital e P&L."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class PortfolioSnapshot:
    total_capital: float
    available_capital: float
    allocated_capital: float
    current_exposure_pct: float
    max_exposure_pct: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    annualized_return_pct: float


def build_portfolio_snapshot(
    *,
    equity: float,
    cash: float,
    allocated: float,
    max_exposure_pct: float = 0.95,
    daily_pnl: float = 0.0,
    weekly_pnl: float = 0.0,
    monthly_pnl: float = 0.0,
    initial_capital: float = 10_000.0,
    started_at: datetime | None = None,
) -> PortfolioSnapshot:
    exposure = allocated / equity if equity > 0 else 0.0
    annualized = 0.0
    if started_at and initial_capital > 0:
        days = max(1, (datetime.now(timezone.utc) - started_at).days)
        growth = equity / initial_capital
        annualized = (growth ** (365 / days) - 1) * 100 if growth > 0 else 0.0
    return PortfolioSnapshot(
        total_capital=round(equity, 2),
        available_capital=round(cash, 2),
        allocated_capital=round(allocated, 2),
        current_exposure_pct=round(exposure * 100, 2),
        max_exposure_pct=round(max_exposure_pct * 100, 2),
        daily_pnl=round(daily_pnl, 2),
        weekly_pnl=round(weekly_pnl, 2),
        monthly_pnl=round(monthly_pnl, 2),
        annualized_return_pct=round(annualized, 2),
    )
