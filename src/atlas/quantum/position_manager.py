"""Position Manager — stops ATR, trailing e sizing."""
from __future__ import annotations

from dataclasses import dataclass

from atlas.core.models import Candle, Position, Signal, SignalAction


@dataclass
class ManagedLevels:
    stop_price: float
    target_price: float
    breakeven_active: bool = False
    trailing_active: bool = False


class PositionManager:
    """Gerencia níveis de stop, alvo e trailing (long only)."""

    def __init__(
        self,
        *,
        stop_atr: float = 1.0,
        target_atr: float = 2.0,
        trailing_atr: float = 1.5,
    ) -> None:
        self.stop_atr = stop_atr
        self.target_atr = target_atr
        self.trailing_atr = trailing_atr

    def levels_for_entry(self, entry_price: float, atr: float) -> ManagedLevels:
        if atr <= 0 or entry_price <= 0:
            stop = entry_price * 0.98
            target = entry_price * 1.04
        else:
            stop = entry_price - self.stop_atr * atr
            target = entry_price + self.target_atr * atr
        return ManagedLevels(stop_price=max(stop, 0.0), target_price=target)

    def update_trailing(
        self,
        position: Position,
        candle: Candle,
        atr: float,
    ) -> ManagedLevels:
        entry = position.entry_price
        stop = position.stop_price or entry * 0.98
        target = position.target_price or entry * 1.04
        risk = entry - stop if entry > stop else entry * 0.01
        reward = candle.high - entry

        breakeven = reward >= risk
        trailing = reward >= risk * 2

        if breakeven and stop < entry:
            stop = entry
        if trailing and atr > 0:
            trail_stop = candle.close - self.trailing_atr * atr
            stop = max(stop, trail_stop)

        return ManagedLevels(
            stop_price=stop,
            target_price=target,
            breakeven_active=breakeven,
            trailing_active=trailing,
        )

    def evaluate_exit(self, position: Position, candle: Candle, atr: float) -> Signal | None:
        levels = self.update_trailing(position, candle, atr)
        if candle.low <= levels.stop_price:
            reason = "trailing stop ATR" if levels.trailing_active else "stop loss 1 ATR"
            if levels.breakeven_active and not levels.trailing_active:
                reason = "breakeven após 1R"
            return Signal(action=SignalAction.EXIT_LONG, reason=reason)
        if levels.target_price and candle.high >= levels.target_price:
            return Signal(action=SignalAction.EXIT_LONG, reason="take profit 2 ATR")
        return None
