from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction


class PullbackShortV1:
    """Repique até EMA20 em tendência de baixa — short only."""

    name = "pullback_short_v1"
    market_type = "bear"
    strategy_category = "bear"

    def __init__(
        self,
        min_adx: float = 20.0,
        pullback_pct: float = 0.008,
        stop_atr_mult: float = 1.0,
        target_atr_mult: float = 2.0,
    ) -> None:
        self.min_adx = min_adx
        self.pullback_pct = pullback_pct
        self.stop_atr_mult = stop_atr_mult
        self.target_atr_mult = target_atr_mult

    def evaluate(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position | None,
    ) -> Signal:
        if position is not None:
            return self._evaluate_exit(candle, indicators, position)
        return self._evaluate_entry(candle, indicators)

    def _ema20_declining(self, indicators: IndicatorSnapshot) -> bool:
        if indicators.ema20 is None or indicators.prev_ema20 is None:
            return indicators.ema20 is not None
        return indicators.ema20 <= indicators.prev_ema20

    def _evaluate_entry(self, candle: Candle, indicators: IndicatorSnapshot) -> Signal:
        if any(v is None for v in (indicators.ema20, indicators.ema200, indicators.adx, indicators.atr)):
            return Signal(action=SignalAction.HOLD, reason="indicators not ready")

        if candle.close >= indicators.ema200:
            return Signal(action=SignalAction.HOLD, reason="above ema200")

        if not self._ema20_declining(indicators):
            return Signal(action=SignalAction.HOLD, reason="ema20 not declining")

        if indicators.adx < self.min_adx:
            return Signal(action=SignalAction.HOLD, reason="adx below threshold")

        repique = candle.high >= indicators.ema20 * (1 - self.pullback_pct)
        rejection = candle.close < indicators.ema20 and candle.close < candle.open
        if not repique:
            return Signal(action=SignalAction.HOLD, reason="no pullback")
        if not rejection:
            return Signal(action=SignalAction.HOLD, reason="no rejection candle")

        atr = float(indicators.atr)
        stop_price = candle.close + self.stop_atr_mult * atr
        target_price = candle.close - self.target_atr_mult * atr
        return Signal(
            action=SignalAction.ENTER_SHORT,
            reason="pullback rejection below ema200 downtrend",
            stop_price=stop_price,
            target_price=target_price,
            metadata={"regime": "bear_pullback", "market_type": "bear"},
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

        if indicators.ema200 is not None and candle.close >= indicators.ema200:
            return Signal(action=SignalAction.EXIT_SHORT, reason="close above ema200 — trend broken")

        if indicators.ema20 is not None and candle.close > indicators.ema20:
            return Signal(action=SignalAction.EXIT_SHORT, reason="close above ema20")

        return Signal(action=SignalAction.HOLD, reason="holding short pullback")


def build_pullback_short_v1(params: dict) -> PullbackShortV1:
    return PullbackShortV1(
        min_adx=float(params.get("min_adx", 20.0)),
        pullback_pct=float(params.get("pullback_pct", 0.008)),
        stop_atr_mult=float(params.get("stop_atr_mult", 1.0)),
        target_atr_mult=float(params.get("target_atr_mult", 2.0)),
    )
