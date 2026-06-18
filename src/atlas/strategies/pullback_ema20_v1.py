from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction


class PullbackEma20V1:
    """Pullback na EMA 20 dentro da tendência da EMA 200 — long only."""

    name = "pullback_ema20_v1"

    def __init__(
        self,
        pullback_pct: float = 0.008,
        stop_below_ema20_pct: float = 0.015,
        require_ema_stack: bool = True,
    ) -> None:
        self.pullback_pct = pullback_pct
        self.stop_below_ema20_pct = stop_below_ema20_pct
        self.require_ema_stack = require_ema_stack

    def evaluate(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position | None,
    ) -> Signal:
        if position is not None:
            return self._evaluate_exit(candle, indicators, position)
        return self._evaluate_entry(candle, indicators)

    def _in_uptrend(self, candle: Candle, indicators: IndicatorSnapshot) -> bool:
        if indicators.ema20 is None or indicators.ema200 is None:
            return False
        if candle.close <= indicators.ema200:
            return False
        if self.require_ema_stack and indicators.ema20 <= indicators.ema200:
            return False
        return True

    def _evaluate_entry(self, candle: Candle, indicators: IndicatorSnapshot) -> Signal:
        if indicators.ema20 is None or indicators.ema200 is None:
            return Signal(action=SignalAction.HOLD, reason="ema not ready")

        if not self._in_uptrend(candle, indicators):
            return Signal(action=SignalAction.HOLD, reason="no uptrend (below ema200)")

        touched = candle.low <= indicators.ema20 * (1 + self.pullback_pct)
        bounced = candle.close > indicators.ema20 and candle.close > candle.open

        if not touched:
            return Signal(action=SignalAction.HOLD, reason="no pullback to ema20")
        if not bounced:
            return Signal(action=SignalAction.HOLD, reason="no bullish bounce on ema20")

        stop_price = indicators.ema20 * (1 - self.stop_below_ema20_pct)
        return Signal(
            action=SignalAction.ENTER_LONG,
            reason="pullback bounce on ema20 in ema200 uptrend",
            stop_price=stop_price,
            metadata={"regime": "trend_pullback"},
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
            return Signal(action=SignalAction.EXIT_LONG, reason="close below ema200 — trend broken")

        if indicators.ema20 is not None and candle.close < indicators.ema20:
            return Signal(action=SignalAction.EXIT_LONG, reason="close below ema20")

        return Signal(action=SignalAction.HOLD, reason="holding pullback long")


def build_pullback_ema20_v1(params: dict) -> PullbackEma20V1:
    return PullbackEma20V1(
        pullback_pct=float(params.get("pullback_pct", 0.008)),
        stop_below_ema20_pct=float(params.get("stop_below_ema20_pct", 0.015)),
        require_ema_stack=bool(params.get("require_ema_stack", True)),
    )
