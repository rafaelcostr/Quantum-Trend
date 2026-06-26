from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction


class SupertrendBearV1:
    """Supertrend bearish + EMA200 — trend following short."""

    name = "supertrend_bear_v1"
    market_type = "bear"
    strategy_category = "bear"

    def __init__(
        self,
        min_adx: float = 20.0,
        stop_atr_mult: float = 1.0,
        target_atr_mult: float = 2.0,
        pullback_pct: float = 0.01,
    ) -> None:
        self.min_adx = min_adx
        self.stop_atr_mult = stop_atr_mult
        self.target_atr_mult = target_atr_mult
        self.pullback_pct = pullback_pct

    def _supertrend_bear(self, candle: Candle, indicators: IndicatorSnapshot) -> bool:
        if indicators.supertrend_dir is None:
            return False
        return indicators.supertrend_dir < 0 and candle.close < (indicators.supertrend or candle.close)

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
        if any(v is None for v in (indicators.ema200, indicators.supertrend, indicators.adx, indicators.atr)):
            return Signal(action=SignalAction.HOLD, reason="indicators not ready")

        if candle.close >= indicators.ema200:
            return Signal(action=SignalAction.HOLD, reason="above ema200")

        if indicators.adx < self.min_adx:
            return Signal(action=SignalAction.HOLD, reason="adx below threshold")

        if not self._supertrend_bear(candle, indicators):
            return Signal(action=SignalAction.HOLD, reason="supertrend bullish")

        repique = candle.high >= min(
            indicators.ema20 or candle.close,
            indicators.supertrend or candle.close,
        ) * (1 - self.pullback_pct)
        if not repique:
            return Signal(action=SignalAction.HOLD, reason="no pullback")

        atr = float(indicators.atr)
        stop_price = max(candle.close + self.stop_atr_mult * atr, (indicators.supertrend or candle.close) * 1.002)
        target_price = candle.close - self.target_atr_mult * atr
        return Signal(
            action=SignalAction.ENTER_SHORT,
            reason="supertrend bear pullback below ema200",
            stop_price=stop_price,
            target_price=target_price,
            metadata={"regime": "bear_supertrend", "market_type": "bear"},
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

        if indicators.supertrend_dir is not None and indicators.supertrend_dir > 0:
            return Signal(action=SignalAction.EXIT_SHORT, reason="supertrend flipped bullish")

        if indicators.supertrend is not None and candle.close > indicators.supertrend:
            return Signal(action=SignalAction.EXIT_SHORT, reason="close above supertrend line")

        if indicators.ema200 is not None and candle.close >= indicators.ema200:
            return Signal(action=SignalAction.EXIT_SHORT, reason="close above ema200")

        return Signal(action=SignalAction.HOLD, reason="holding short supertrend")


def build_supertrend_bear_v1(params: dict) -> SupertrendBearV1:
    return SupertrendBearV1(
        min_adx=float(params.get("min_adx", 20.0)),
        stop_atr_mult=float(params.get("stop_atr_mult", 1.0)),
        target_atr_mult=float(params.get("target_atr_mult", 2.0)),
        pullback_pct=float(params.get("pullback_pct", 0.01)),
    )
