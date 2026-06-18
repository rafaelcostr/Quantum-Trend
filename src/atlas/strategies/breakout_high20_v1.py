from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction


class BreakoutHigh20V1:
    """Breakout da máxima de N períodos com filtro de volume — long only."""

    name = "breakout_high20_v1"

    def __init__(
        self,
        volume_mult: float = 1.2,
        stop_pct: float = 0.025,
        min_adx: float = 15.0,
    ) -> None:
        self.volume_mult = volume_mult
        self.stop_pct = stop_pct
        self.min_adx = min_adx

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
        if indicators.high_20 is None:
            return Signal(action=SignalAction.HOLD, reason="high lookback not ready")

        if candle.close <= indicators.high_20:
            return Signal(action=SignalAction.HOLD, reason="no breakout above high20")

        if not self._volume_ok(candle, indicators):
            return Signal(action=SignalAction.HOLD, reason="volume below threshold")

        if indicators.adx is not None and indicators.adx < self.min_adx:
            return Signal(action=SignalAction.HOLD, reason=f"adx too low ({indicators.adx:.1f})")

        stop_price = max(candle.close * (1 - self.stop_pct), indicators.high_20 * 0.995)
        return Signal(
            action=SignalAction.ENTER_LONG,
            reason="breakout high20 with volume confirmation",
            stop_price=stop_price,
            metadata={"regime": "breakout"},
        )

    def _evaluate_exit(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position,
    ) -> Signal:
        if position.stop_price and candle.low <= position.stop_price:
            return Signal(action=SignalAction.EXIT_LONG, reason="stop loss hit")

        if indicators.high_20 is not None and candle.close < indicators.high_20:
            return Signal(action=SignalAction.EXIT_LONG, reason="close back below breakout level")

        if indicators.ema20 is not None and candle.close < indicators.ema20:
            return Signal(action=SignalAction.EXIT_LONG, reason="close below ema20")

        return Signal(action=SignalAction.HOLD, reason="holding breakout long")


def build_breakout_high20_v1(params: dict) -> BreakoutHigh20V1:
    return BreakoutHigh20V1(
        volume_mult=float(params.get("volume_mult", 1.2)),
        stop_pct=float(params.get("stop_pct", 0.025)),
        min_adx=float(params.get("min_adx", 15.0)),
    )
