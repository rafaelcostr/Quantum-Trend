from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction


class SupertrendMm200V1:
    """Supertrend bullish + preço acima EMA 200 + ADX mínimo — long only."""

    name = "supertrend_mm200_v1"

    def __init__(
        self,
        min_adx: float = 20.0,
        stop_below_ema200_pct: float = 0.02,
    ) -> None:
        self.min_adx = min_adx
        self.stop_below_ema200_pct = stop_below_ema200_pct

    def evaluate(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position | None,
    ) -> Signal:
        if position is not None:
            return self._evaluate_exit(candle, indicators, position)
        return self._evaluate_entry(candle, indicators)

    def _supertrend_bull(self, candle: Candle, indicators: IndicatorSnapshot) -> bool:
        if indicators.supertrend_dir is None:
            return False
        return indicators.supertrend_dir >= 1 and candle.close > (indicators.supertrend or 0)

    def _evaluate_entry(self, candle: Candle, indicators: IndicatorSnapshot) -> Signal:
        if any(v is None for v in (indicators.ema200, indicators.supertrend, indicators.adx)):
            return Signal(action=SignalAction.HOLD, reason="indicators not ready")

        if candle.close <= indicators.ema200:
            return Signal(action=SignalAction.HOLD, reason="below ema200")

        if indicators.adx < self.min_adx:
            return Signal(action=SignalAction.HOLD, reason=f"adx too low ({indicators.adx:.1f})")

        if not self._supertrend_bull(candle, indicators):
            return Signal(action=SignalAction.HOLD, reason="supertrend not bullish")

        stop_price = min(
            indicators.ema200 * (1 - self.stop_below_ema200_pct),
            (indicators.supertrend or candle.close) * 0.995,
        )
        return Signal(
            action=SignalAction.ENTER_LONG,
            reason="supertrend bull + above ema200 + adx filter",
            stop_price=stop_price,
            metadata={"regime": "supertrend_trend"},
        )

    def _evaluate_exit(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position,
    ) -> Signal:
        if position.stop_price and candle.low <= position.stop_price:
            return Signal(action=SignalAction.EXIT_LONG, reason="stop loss hit")

        if indicators.ema200 is not None and candle.close < indicators.ema200:
            return Signal(action=SignalAction.EXIT_LONG, reason="close below ema200")

        if indicators.supertrend_dir is not None and indicators.supertrend_dir < 0:
            return Signal(action=SignalAction.EXIT_LONG, reason="supertrend flipped bearish")

        if indicators.supertrend is not None and candle.close < indicators.supertrend:
            return Signal(action=SignalAction.EXIT_LONG, reason="close below supertrend line")

        return Signal(action=SignalAction.HOLD, reason="holding supertrend long")


def build_supertrend_mm200_v1(params: dict) -> SupertrendMm200V1:
    return SupertrendMm200V1(
        min_adx=float(params.get("min_adx", 20.0)),
        stop_below_ema200_pct=float(params.get("stop_below_ema200_pct", 0.02)),
    )
