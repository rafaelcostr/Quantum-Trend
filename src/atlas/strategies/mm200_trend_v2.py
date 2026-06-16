from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction


class MM200TrendV2:
    """MM200 crossover — enter on bullish cross, exit on bearish cross (fewer whipsaws)."""

    name = "mm200_trend_v2"

    def __init__(self, stop_below_mm200_pct: float = 0.02) -> None:
        self.stop_below_mm200_pct = stop_below_mm200_pct

    def evaluate(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position | None,
    ) -> Signal:
        if indicators.mm200 is None or indicators.prev_close is None:
            return Signal(action=SignalAction.HOLD, reason="mm200 not ready")

        if position is not None:
            bearish_cross = (
                indicators.prev_close >= indicators.mm200 and candle.close < indicators.mm200
            )
            if bearish_cross:
                return Signal(action=SignalAction.EXIT_LONG, reason="bearish cross below mm200")
            return Signal(action=SignalAction.HOLD, reason="holding — no bearish cross")

        bullish_cross = (
            indicators.prev_close <= indicators.mm200 and candle.close > indicators.mm200
        )
        if bullish_cross:
            stop_price = indicators.mm200 * (1 - self.stop_below_mm200_pct)
            return Signal(
                action=SignalAction.ENTER_LONG,
                reason="bullish cross above mm200",
                stop_price=stop_price,
                metadata={"regime": "bull", "sleeve": "macro", "allocation_pct": 1.0},
            )

        return Signal(action=SignalAction.HOLD, reason="no crossover")


def build_mm200_trend_v2(params: dict) -> MM200TrendV2:
    return MM200TrendV2(
        stop_below_mm200_pct=float(params.get("stop_below_mm200_pct", 0.02)),
    )
