from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from atlas.core.models import PortfolioState, RiskConfig, Signal, SignalAction


@dataclass
class RiskDecision:
    approved: bool
    reason: str = ""
    quantity: float = 0.0


@dataclass
class RiskManager:
    config: RiskConfig
    kill_switch: bool = False
    _daily_start_equity: float | None = field(default=None, init=False)
    _weekly_start_equity: float | None = field(default=None, init=False)
    _last_day: int | None = field(default=None, init=False)
    _last_week: int | None = field(default=None, init=False)

    def activate_kill_switch(self, reason: str = "manual") -> None:
        self.kill_switch = True

    def deactivate_kill_switch(self) -> None:
        self.kill_switch = False

    def _roll_periods(self, now: datetime, equity: float) -> None:
        day = now.timetuple().tm_yday
        week = now.isocalendar()[1]
        if self._last_day != day:
            self._daily_start_equity = equity
            self._last_day = day
        if self._last_week != week:
            self._weekly_start_equity = equity
            self._last_week = week

    def _drawdown_exceeded(self, equity: float) -> str | None:
        if self._daily_start_equity and self._daily_start_equity > 0:
            dd = (self._daily_start_equity - equity) / self._daily_start_equity
            if dd >= self.config.max_daily_drawdown:
                return f"daily drawdown limit ({dd:.2%})"
        if self._weekly_start_equity and self._weekly_start_equity > 0:
            dd = (self._weekly_start_equity - equity) / self._weekly_start_equity
            if dd >= self.config.max_weekly_drawdown:
                return f"weekly drawdown limit ({dd:.2%})"
        return None

    def position_size(self, equity: float, entry_price: float, stop_price: float) -> float:
        if entry_price <= 0 or stop_price <= 0:
            return 0.0
        risk_amount = equity * self.config.risk_per_trade
        risk_per_unit = abs(entry_price - stop_price)
        if risk_per_unit == 0:
            return 0.0
        qty = risk_amount / risk_per_unit
        max_qty = equity / entry_price
        return min(qty, max_qty)

    def approve_entry(
        self,
        signal: Signal,
        portfolio: PortfolioState,
        now: datetime,
        entry_price: float,
    ) -> RiskDecision:
        if self.kill_switch:
            return RiskDecision(False, "kill switch active")
        if signal.action not in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            return RiskDecision(False, "not an entry signal")
        if portfolio.position is not None:
            return RiskDecision(False, "position already open")
        if self.config.max_open_positions < 1:
            return RiskDecision(False, "max positions reached")

        self._roll_periods(now, portfolio.equity)
        dd_reason = self._drawdown_exceeded(portfolio.equity)
        if dd_reason:
            return RiskDecision(False, dd_reason)

        if self.config.sizing_mode == "full_equity":
            alloc = float(signal.metadata.get("allocation_pct", 1.0))
            qty = (portfolio.cash * 0.99 * alloc) / entry_price
        else:
            if signal.stop_price is None:
                return RiskDecision(False, "entry requires stop_price")
            qty = self.position_size(portfolio.equity, entry_price, signal.stop_price)
        if qty <= 0:
            return RiskDecision(False, "position size is zero")
        return RiskDecision(True, "approved", quantity=qty)

    def approve_exit(self, signal: Signal, portfolio: PortfolioState) -> RiskDecision:
        if signal.action not in (SignalAction.EXIT_LONG, SignalAction.EXIT_SHORT):
            return RiskDecision(False, "not an exit signal")
        if portfolio.position is None:
            return RiskDecision(False, "no open position")
        return RiskDecision(True, "approved", quantity=portfolio.position.quantity)

    # compat legado risk_store
    def update_peak(self, equity: float) -> None:
        pass

    def drawdown_pct(self, equity: float) -> float:
        return 0.0

    def allows_new_entry(self, equity: float) -> bool:
        return not self.kill_switch

    def stop_price(self, entry: float) -> float:
        return entry * (1 - self.config.stop_loss_pct)

    def target_price(self, entry: float) -> float:
        return entry * (1 + self.config.take_profit_pct)
