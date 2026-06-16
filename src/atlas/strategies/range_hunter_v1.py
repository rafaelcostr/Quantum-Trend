from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction


class RangeHunterV1:
    """
    Mean-reversion long-only strategy for ranging markets.
    BB lower touch + RSI oversold + ADX range filter + optional S/R confluence.
    """

    name = "range_hunter_v1"

    def __init__(
        self,
        rsi_long_max: float = 38.0,
        adx_max: float = 25.0,
        stop_pct: float = 0.025,
        require_sr: bool = False,
    ) -> None:
        self.rsi_long_max = rsi_long_max
        self.adx_max = adx_max
        self.stop_pct = stop_pct
        self.require_sr = require_sr

    def evaluate(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position | None,
    ) -> Signal:
        if position is not None:
            return self._evaluate_exit(candle, indicators, position)
        return self._evaluate_entry(candle, indicators)

    def _evaluate_entry(self, candle: Candle, indicators: IndicatorSnapshot) -> Signal:
        if any(
            v is None
            for v in (indicators.bb_lower, indicators.bb_mid, indicators.rsi, indicators.adx)
        ):
            return Signal(action=SignalAction.HOLD, reason="indicators not ready")

        if indicators.adx > self.adx_max:
            return Signal(action=SignalAction.HOLD, reason=f"adx too high ({indicators.adx:.1f})")

        if candle.close >= indicators.bb_lower:
            return Signal(action=SignalAction.HOLD, reason="price above lower band")

        if indicators.rsi >= self.rsi_long_max:
            return Signal(action=SignalAction.HOLD, reason=f"rsi not oversold ({indicators.rsi:.1f})")

        if self.require_sr and indicators.support is None:
            return Signal(action=SignalAction.HOLD, reason="no support confluence")

        stop_price = candle.close * (1 - self.stop_pct)
        if indicators.support is not None:
            stop_price = min(stop_price, indicators.support * 0.995)

        return Signal(
            action=SignalAction.ENTER_LONG,
            reason="bb lower + rsi oversold in range (adx filter)",
            stop_price=stop_price,
            target_price=indicators.bb_mid,
        )

    def _evaluate_exit(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position,
    ) -> Signal:
        if position.stop_price and candle.low <= position.stop_price:
            return Signal(action=SignalAction.EXIT_LONG, reason="stop loss hit")

        if position.target_price and candle.high >= position.target_price:
            return Signal(action=SignalAction.EXIT_LONG, reason="take profit at bb mid")

        if indicators.bb_mid is not None and candle.close >= indicators.bb_mid:
            return Signal(action=SignalAction.EXIT_LONG, reason="close above bb mid")

        if indicators.adx is not None and indicators.adx > self.adx_max + 10:
            return Signal(action=SignalAction.EXIT_LONG, reason="regime shifted to trend")

        return Signal(action=SignalAction.HOLD, reason="holding long")


def build_range_hunter_v1(params: dict) -> RangeHunterV1:
    return RangeHunterV1(
        rsi_long_max=float(params.get("rsi_long_max", 38)),
        adx_max=float(params.get("adx_max", 25)),
        stop_pct=float(params.get("stop_pct", 0.025)),
        require_sr=bool(params.get("require_sr", False)),
    )
