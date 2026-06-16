from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction


class RegimeSwitchingV1:
    """
    Regime-aware strategy for BTC 4H:
    - RANGE (ADX < range_adx_max): mean reversion at support + BB lower (Range Hunter v2)
    - TREND UP (ADX > trend_adx_min, close > MM200): pullback to MM20 / BB mid
    - UNCERTAIN: no new entries
    """

    name = "regime_switching_v1"

    def __init__(
        self,
        range_adx_max: float = 20.0,
        trend_adx_min: float = 25.0,
        rsi_long_max: float = 38.0,
        rsi_pullback_min: float = 40.0,
        rsi_pullback_max: float = 65.0,
        stop_pct: float = 0.025,
        risk_reward: float = 2.5,
        pullback_mm20_pct: float = 0.01,
        enable_trend_entries: bool = False,
        require_above_mm200_for_range: bool = True,
    ) -> None:
        self.range_adx_max = range_adx_max
        self.trend_adx_min = trend_adx_min
        self.rsi_long_max = rsi_long_max
        self.rsi_pullback_min = rsi_pullback_min
        self.rsi_pullback_max = rsi_pullback_max
        self.stop_pct = stop_pct
        self.risk_reward = risk_reward
        self.pullback_mm20_pct = pullback_mm20_pct
        self.enable_trend_entries = enable_trend_entries
        self.require_above_mm200_for_range = require_above_mm200_for_range

    def _regime(self, candle: Candle, indicators: IndicatorSnapshot) -> str:
        if indicators.adx is None or indicators.mm200 is None:
            return "unknown"
        if indicators.adx < self.range_adx_max:
            return "range"
        if indicators.adx > self.trend_adx_min and candle.close > indicators.mm200:
            return "trend_up"
        return "uncertain"

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
        regime = self._regime(candle, indicators)
        if regime == "range":
            return self._range_entry(candle, indicators)
        if regime == "trend_up" and self.enable_trend_entries:
            return self._trend_entry(candle, indicators)
        return Signal(action=SignalAction.HOLD, reason=f"no entry ({regime})")

    def _range_entry(self, candle: Candle, indicators: IndicatorSnapshot) -> Signal:
        if any(
            v is None
            for v in (indicators.bb_lower, indicators.bb_mid, indicators.rsi, indicators.adx)
        ):
            return Signal(action=SignalAction.HOLD, reason="indicators not ready")

        if candle.close >= indicators.bb_lower:
            return Signal(action=SignalAction.HOLD, reason="price above lower band")

        if indicators.rsi >= self.rsi_long_max:
            return Signal(action=SignalAction.HOLD, reason=f"rsi not oversold ({indicators.rsi:.1f})")

        if self.require_above_mm200_for_range and indicators.mm200 is not None:
            if candle.close <= indicators.mm200:
                return Signal(action=SignalAction.HOLD, reason="below mm200 — no range entry")

        if indicators.support is None:
            return Signal(action=SignalAction.HOLD, reason="no support confluence")

        stop_price = candle.close * (1 - self.stop_pct)
        stop_price = min(stop_price, indicators.support * 0.995)

        return Signal(
            action=SignalAction.ENTER_LONG,
            reason="range: bb lower + rsi + support",
            stop_price=stop_price,
            target_price=indicators.bb_mid,
            metadata={"regime": "range"},
        )

    def _trend_entry(self, candle: Candle, indicators: IndicatorSnapshot) -> Signal:
        if any(
            v is None
            for v in (indicators.mm20, indicators.mm200, indicators.rsi, indicators.adx, indicators.atr)
        ):
            return Signal(action=SignalAction.HOLD, reason="indicators not ready")

        if candle.close <= indicators.mm200:
            return Signal(action=SignalAction.HOLD, reason="below mm200")

        if not (self.rsi_pullback_min <= indicators.rsi <= self.rsi_pullback_max):
            return Signal(action=SignalAction.HOLD, reason=f"rsi out of pullback band ({indicators.rsi:.1f})")

        touched_mm20 = candle.low <= indicators.mm20 * (1 + self.pullback_mm20_pct)
        touched_bb_mid = (
            indicators.bb_mid is not None
            and candle.low <= indicators.bb_mid * 1.01
            and candle.close > indicators.mm20
        )
        if not (touched_mm20 or touched_bb_mid):
            return Signal(action=SignalAction.HOLD, reason="no pullback to mm20/bb mid")

        # Bounce confirmation: closed back above MM20 after touching it
        if touched_mm20 and candle.close < indicators.mm20:
            return Signal(action=SignalAction.HOLD, reason="no bounce above mm20")

        if candle.close <= candle.open:
            return Signal(action=SignalAction.HOLD, reason="not a bullish candle")

        stop_price = min(
            indicators.mm20 * (1 - self.stop_pct),
            candle.close - 2 * indicators.atr,
        )
        risk = candle.close - stop_price
        if risk <= 0:
            return Signal(action=SignalAction.HOLD, reason="invalid stop distance")

        target_price = candle.close + risk * self.risk_reward
        if indicators.resistance is not None and indicators.resistance > candle.close:
            target_price = min(target_price, indicators.resistance)

        return Signal(
            action=SignalAction.ENTER_LONG,
            reason="trend: pullback to mm20/bb mid above mm200",
            stop_price=stop_price,
            target_price=target_price,
            metadata={"regime": "trend_up"},
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
            return Signal(action=SignalAction.EXIT_LONG, reason="take profit hit")

        if indicators.mm200 is not None and candle.close < indicators.mm200:
            return Signal(action=SignalAction.EXIT_LONG, reason="close below mm200")

        if (
            indicators.mm20 is not None
            and indicators.adx is not None
            and indicators.adx > self.trend_adx_min
            and candle.close < indicators.mm20
        ):
            return Signal(action=SignalAction.EXIT_LONG, reason="trend broken below mm20")

        if indicators.adx is not None and indicators.adx > self.trend_adx_min + 15:
            return Signal(action=SignalAction.EXIT_LONG, reason="adx extreme — take profit")

        return Signal(action=SignalAction.HOLD, reason="holding long")


def build_regime_switching_v1(params: dict) -> RegimeSwitchingV1:
    return RegimeSwitchingV1(
        range_adx_max=float(params.get("range_adx_max", 20)),
        trend_adx_min=float(params.get("trend_adx_min", 25)),
        rsi_long_max=float(params.get("rsi_long_max", 38)),
        rsi_pullback_min=float(params.get("rsi_pullback_min", 40)),
        rsi_pullback_max=float(params.get("rsi_pullback_max", 65)),
        stop_pct=float(params.get("stop_pct", 0.025)),
        risk_reward=float(params.get("risk_reward", 2.5)),
        pullback_mm20_pct=float(params.get("pullback_mm20_pct", 0.01)),
        enable_trend_entries=bool(params.get("enable_trend_entries", False)),
        require_above_mm200_for_range=bool(params.get("require_above_mm200_for_range", True)),
    )
