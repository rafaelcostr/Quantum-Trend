from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction


class MM200TrendV1:
    """
    Buy & Hold enhancer — long when close > MM200, flat when close < MM200.
    Minimal trend filter to avoid holding through deep bear phases.
    """

    name = "mm200_trend_v1"

    def __init__(self, stop_below_mm200_pct: float = 0.02) -> None:
        self.stop_below_mm200_pct = stop_below_mm200_pct

    def evaluate(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position | None,
    ) -> Signal:
        if indicators.mm200 is None:
            return Signal(action=SignalAction.HOLD, reason="mm200 not ready")

        if position is not None:
            if candle.close < indicators.mm200:
                return Signal(action=SignalAction.EXIT_LONG, reason="close below mm200")
            return Signal(action=SignalAction.HOLD, reason="holding above mm200")

        if candle.close > indicators.mm200:
            stop_price = indicators.mm200 * (1 - self.stop_below_mm200_pct)
            return Signal(
                action=SignalAction.ENTER_LONG,
                reason="close above mm200",
                stop_price=stop_price,
                target_price=None,
                metadata={"regime": "bull"},
            )

        return Signal(action=SignalAction.HOLD, reason="below mm200 — stay flat")


def build_mm200_trend_v1(params: dict) -> MM200TrendV1:
    return MM200TrendV1(
        stop_below_mm200_pct=float(params.get("stop_below_mm200_pct", 0.02)),
    )
