from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction
from atlas.strategies.mm200_trend_v2 import MM200TrendV2
from atlas.strategies.range_hunter_v2 import RangeHunterV2


class PortfolioMacroMicroV1:
    """
    Portfolio: daily macro gate + micro range trades (30%) + macro MM200 crossover (70%).
    Only one position at a time; micro has priority when both signal.
    """

    name = "portfolio_macro_micro_v1"

    def __init__(
        self,
        micro_allocation: float = 0.30,
        macro_allocation: float = 0.70,
        range_adx_max: float = 25.0,
        stop_pct: float = 0.025,
        stop_below_mm200_pct: float = 0.02,
    ) -> None:
        self.micro_allocation = micro_allocation
        self.macro_allocation = macro_allocation
        self.range = RangeHunterV2(rsi_long_max=38, adx_max=range_adx_max, stop_pct=stop_pct)
        self.macro = MM200TrendV2(stop_below_mm200_pct=stop_below_mm200_pct)

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

        sleeve = (position.metadata.get("sleeve") if position else None) or "macro"

        if position is not None:
            if not self._macro_ok(indicators):
                return Signal(action=SignalAction.EXIT_LONG, reason="daily macro off")
            if sleeve == "micro":
                return self.range.evaluate(candle, indicators, position)
            return self.macro.evaluate(candle, indicators, position)

        if not self._macro_ok(indicators):
            return Signal(action=SignalAction.HOLD, reason="daily macro bear")

        micro = self.range.evaluate(candle, indicators, None)
        if micro.action == SignalAction.ENTER_LONG:
            micro.metadata = {
                **micro.metadata,
                "sleeve": "micro",
                "allocation_pct": self.micro_allocation,
            }
            return micro

        macro = self.macro.evaluate(candle, indicators, None)
        if macro.action == SignalAction.ENTER_LONG:
            macro.metadata = {
                **macro.metadata,
                "sleeve": "macro",
                "allocation_pct": self.macro_allocation,
            }
            return macro

        return Signal(action=SignalAction.HOLD, reason="no micro or macro setup")


def build_portfolio_macro_micro_v1(params: dict) -> PortfolioMacroMicroV1:
    return PortfolioMacroMicroV1(
        micro_allocation=float(params.get("micro_allocation", 0.30)),
        macro_allocation=float(params.get("macro_allocation", 0.70)),
        range_adx_max=float(params.get("range_adx_max", 25)),
        stop_pct=float(params.get("stop_pct", 0.025)),
        stop_below_mm200_pct=float(params.get("stop_below_mm200_pct", 0.02)),
    )
