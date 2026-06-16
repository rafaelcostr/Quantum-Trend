from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction
from atlas.strategies.mm200_trend_v2 import MM200TrendV2


class MM200DailyMacroV1:
    """4H MM200 crossover entries only when daily macro filter is bullish."""

    name = "mm200_daily_macro_v1"

    def __init__(self, stop_below_mm200_pct: float = 0.02) -> None:
        self.trend = MM200TrendV2(stop_below_mm200_pct=stop_below_mm200_pct)

    def _macro_ok(self, indicators: IndicatorSnapshot) -> bool:
        return indicators.macro_bull is True

    def evaluate(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position | None,
    ) -> Signal:
        if indicators.mm200_daily is None:
            return Signal(action=SignalAction.HOLD, reason="daily macro not ready")

        if position is not None:
            if not self._macro_ok(indicators):
                return Signal(action=SignalAction.EXIT_LONG, reason="daily macro turned bear")
            return self.trend.evaluate(candle, indicators, position)

        if not self._macro_ok(indicators):
            return Signal(action=SignalAction.HOLD, reason="daily macro bear — flat")

        signal = self.trend.evaluate(candle, indicators, position)
        if signal.action == SignalAction.ENTER_LONG:
            signal.metadata["filter"] = "daily_macro"
        return signal


def build_mm200_daily_macro_v1(params: dict) -> MM200DailyMacroV1:
    return MM200DailyMacroV1(
        stop_below_mm200_pct=float(params.get("stop_below_mm200_pct", 0.02)),
    )
