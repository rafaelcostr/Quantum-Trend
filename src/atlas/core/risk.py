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
    _peak_equity: float = field(default=0.0, init=False)
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

    def _risk_multiplier(self, equity: float, metadata: dict | None = None) -> float:
        metadata = metadata or {}
        multiplier = 1.0
        if self.config.drawdown_scaling and self._peak_equity > 0:
            dd = max(0.0, (self._peak_equity - equity) / self._peak_equity)
            if dd > 0:
                multiplier *= max(0.25, 1.0 - dd / max(self.config.max_drawdown_pct, 0.01))
        vol = float(metadata.get("volatility_pct", metadata.get("realized_volatility_pct", 0)) or 0)
        if self.config.target_volatility_pct > 0 and vol > 0:
            multiplier *= min(1.5, self.config.target_volatility_pct / vol)
        kelly = metadata.get("kelly_fraction")
        if kelly is not None:
            multiplier *= max(0.0, min(1.0, float(kelly) * self.config.fractional_kelly / max(self.config.risk_per_trade, 0.0001)))
        return max(0.05, min(1.5, multiplier))

    def position_size(
        self,
        equity: float,
        entry_price: float,
        stop_price: float | None,
        *,
        metadata: dict | None = None,
    ) -> float:
        if entry_price <= 0 or stop_price is None or stop_price <= 0:
            atr = float((metadata or {}).get("atr", 0) or 0)
            if atr <= 0 or self.config.atr_risk_multiplier <= 0:
                return 0.0
            risk_per_unit = atr * self.config.atr_risk_multiplier
        else:
            risk_per_unit = abs(entry_price - stop_price)
        risk_amount = equity * self.config.risk_per_trade * self._risk_multiplier(equity, metadata)
        if risk_per_unit == 0:
            return 0.0
        qty = risk_amount / risk_per_unit
        max_qty = (equity * self.config.max_exposure_pct) / entry_price
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
        self.update_peak(portfolio.equity)
        dd_reason = self._drawdown_exceeded(portfolio.equity)
        if dd_reason:
            return RiskDecision(False, dd_reason)

        if self.config.sizing_mode == "full_equity":
            alloc = float(signal.metadata.get("allocation_pct", 1.0))
            qty = (portfolio.cash * 0.99 * alloc) / entry_price
        else:
            if signal.stop_price is None and not signal.metadata.get("atr"):
                return RiskDecision(False, "entry requires stop_price")
            qty = self.position_size(
                portfolio.equity,
                entry_price,
                signal.stop_price,
                metadata=signal.metadata,
            )
        if qty <= 0:
            return RiskDecision(False, "position size is zero")
        try:
            from atlas.runtime.portfolio_risk import evaluate_entry_risk

            portfolio_decision = evaluate_entry_risk(
                config=self.config,
                equity=portfolio.equity,
                symbol=str(signal.metadata.get("symbol") or ""),
                strategy=str(signal.metadata.get("strategy") or ""),
                timeframe=str(signal.metadata.get("timeframe") or ""),
                side="short" if signal.action == SignalAction.ENTER_SHORT else "long",
                proposed_notional=qty * entry_price,
                slot=str(signal.metadata.get("slot") or "") or None,
            )
            if not portfolio_decision.approved:
                return RiskDecision(False, portfolio_decision.reason)
            qty *= portfolio_decision.scale
            if qty <= 0:
                return RiskDecision(False, "portfolio risk scaled position to zero")
            reason = portfolio_decision.reason
        except Exception:
            reason = "approved"
        return RiskDecision(True, reason, quantity=qty)

    def approve_exit(self, signal: Signal, portfolio: PortfolioState) -> RiskDecision:
        if signal.action not in (SignalAction.EXIT_LONG, SignalAction.EXIT_SHORT):
            return RiskDecision(False, "not an exit signal")
        if portfolio.position is None:
            return RiskDecision(False, "no open position")
        return RiskDecision(True, "approved", quantity=portfolio.position.quantity)

    # compat legado risk_store
    def update_peak(self, equity: float) -> None:
        self._peak_equity = max(self._peak_equity, equity)

    def drawdown_pct(self, equity: float) -> float:
        if self._peak_equity <= 0:
            return 0.0
        return max(0.0, (self._peak_equity - equity) / self._peak_equity)

    def allows_new_entry(self, equity: float) -> bool:
        self.update_peak(equity)
        return not self.kill_switch and self.drawdown_pct(equity) < self.config.max_drawdown_pct

    def stop_price(self, entry: float) -> float:
        return entry * (1 - self.config.stop_loss_pct)

    def target_price(self, entry: float) -> float:
        return entry * (1 + self.config.take_profit_pct)
