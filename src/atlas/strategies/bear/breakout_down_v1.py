from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction


class BreakoutDownV1:
    """Rompimento da mínima de 20 candles com volume — short only."""

    name = "breakout_down_v1"
    market_type = "bear"
    strategy_category = "bear"

    def __init__(
        self,
        volume_mult: float = 1.0,
        risk_reward: float = 2.0,
    ) -> None:
        self.volume_mult = volume_mult
        self.risk_reward = risk_reward

    def evaluate(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position | None,
    ) -> Signal:
        if position is not None:
            return self._evaluate_exit(candle, indicators, position)
        return self._evaluate_entry(candle, indicators)

    def _volume_ok(self, candle: Candle, indicators: IndicatorSnapshot) -> bool:
        if indicators.volume_sma20 is None or indicators.volume_sma20 <= 0:
            return candle.volume > 0
        return candle.volume >= indicators.volume_sma20 * self.volume_mult

    def _evaluate_entry(self, candle: Candle, indicators: IndicatorSnapshot) -> Signal:
        if indicators.low_20 is None or indicators.ema200 is None:
            return Signal(action=SignalAction.HOLD, reason="indicators not ready")

        if candle.close >= indicators.ema200:
            return Signal(action=SignalAction.HOLD, reason="above ema200")

        if candle.close >= indicators.low_20:
            return Signal(action=SignalAction.HOLD, reason="no breakdown")

        if not self._volume_ok(candle, indicators):
            return Signal(action=SignalAction.HOLD, reason="insufficient volume")

        stop_price = candle.high * 1.001
        risk = max(stop_price - candle.close, candle.close * 0.005)
        target_price = candle.close - risk * self.risk_reward
        return Signal(
            action=SignalAction.ENTER_SHORT,
            reason="breakdown below low20 with volume",
            stop_price=stop_price,
            target_price=target_price,
            metadata={"regime": "bear_breakdown", "market_type": "bear"},
        )

    def _evaluate_exit(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position,
    ) -> Signal:
        if position.stop_price and candle.high >= position.stop_price:
            return Signal(action=SignalAction.EXIT_SHORT, reason="stop loss hit")

        if position.target_price and candle.low <= position.target_price:
            return Signal(action=SignalAction.EXIT_SHORT, reason="take profit hit")

        if indicators.low_20 is not None and candle.close > indicators.low_20:
            return Signal(action=SignalAction.EXIT_SHORT, reason="breakout not confirmed — back above low20")

        return Signal(action=SignalAction.HOLD, reason="holding short breakdown")


def build_breakout_down_v1(params: dict) -> BreakoutDownV1:
    return BreakoutDownV1(
        volume_mult=float(params.get("volume_mult", 1.0)),
        risk_reward=float(params.get("risk_reward", 2.0)),
    )
