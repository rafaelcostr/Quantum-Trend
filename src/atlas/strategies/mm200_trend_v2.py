from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction


class MM200TrendV2:
    """MM200 crossover — enter on bullish cross, exit on bearish cross."""

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
    return MM200TrendV2(stop_below_mm200_pct=float(params.get("stop_below_mm200_pct", 0.02)))


STRATEGY_LABELS = {
    "mm200_trend_v2": "MM200 Trend v2",
    "mm200_trend_v1": "MM200 Trend v1",
    "range_hunter_v1": "Range Hunter v1",
    "range_hunter_v2": "Range Hunter v2",
    "bb_squeeze_v1": "BB Squeeze v1",
    "regime_switching_v1": "Regime Switching v1",
    "mm200_daily_macro_v1": "MM200 Daily Macro v1",
    "portfolio_macro_micro_v1": "Portfolio Macro/Micro v1",
    "pullback_ema20_v1": "Pullback EMA20 v1",
    "breakout_high20_v1": "Breakout High20 v1",
    "supertrend_mm200_v1": "Supertrend + EMA200 v1",
    "pullback_short_v1": "Pullback Short v1",
    "breakout_down_v1": "Breakout Down v1",
    "supertrend_bear_v1": "Supertrend Bear v1",
    "quantum_trend_pro": "QuantumTrend Pro",
}


def strategy_display_name(name: str) -> str:
    return STRATEGY_LABELS.get(name, name.replace("_", " ").title())
