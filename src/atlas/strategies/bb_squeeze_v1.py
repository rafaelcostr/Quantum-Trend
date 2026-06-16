from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction


class BBSqueezeV1:
    """
    Bollinger squeeze breakout — long-only.
    Enter when bandwidth was compressed and price closes above upper band.
    """

    name = "bb_squeeze_v1"

    def __init__(
        self,
        squeeze_max: float = 0.04,
        stop_pct: float = 0.025,
        target_band_mult: float = 2.0,
        min_adx: float = 18.0,
    ) -> None:
        self.squeeze_max = squeeze_max
        self.stop_pct = stop_pct
        self.target_band_mult = target_band_mult
        self.min_adx = min_adx

    def evaluate(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position | None,
    ) -> Signal:
        if position is not None:
            return self._evaluate_exit(candle, indicators, position)
        return self._evaluate_entry(candle, indicators)

    def _band_width(self, indicators: IndicatorSnapshot) -> float | None:
        if indicators.bb_width is not None:
            return indicators.bb_width
        if (
            indicators.bb_upper is not None
            and indicators.bb_lower is not None
            and indicators.bb_mid
            and indicators.bb_mid > 0
        ):
            return (indicators.bb_upper - indicators.bb_lower) / indicators.bb_mid
        return None

    def _evaluate_entry(self, candle: Candle, indicators: IndicatorSnapshot) -> Signal:
        if any(v is None for v in (indicators.bb_upper, indicators.bb_lower, indicators.bb_mid)):
            return Signal(action=SignalAction.HOLD, reason="indicators not ready")

        prev_width = indicators.prev_bb_width
        if prev_width is None or prev_width >= self.squeeze_max:
            return Signal(action=SignalAction.HOLD, reason="no squeeze on prior bar")

        if candle.close <= indicators.bb_upper:
            return Signal(action=SignalAction.HOLD, reason="no breakout above upper band")

        if indicators.adx is not None and indicators.adx < self.min_adx:
            return Signal(action=SignalAction.HOLD, reason=f"adx too low ({indicators.adx:.1f})")

        width = self._band_width(indicators) or 0.0
        band_range = (indicators.bb_upper - indicators.bb_lower) if width else 0.0
        stop_price = max(
            indicators.bb_lower,
            candle.close * (1 - self.stop_pct),
        )
        target_price = candle.close + band_range * self.target_band_mult

        if indicators.resistance is not None and indicators.resistance > candle.close:
            target_price = min(target_price, indicators.resistance)

        return Signal(
            action=SignalAction.ENTER_LONG,
            reason="bb squeeze breakout above upper band",
            stop_price=stop_price,
            target_price=target_price,
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

        if indicators.bb_mid is not None and candle.close < indicators.bb_mid:
            return Signal(action=SignalAction.EXIT_LONG, reason="close below bb mid (failed breakout)")

        return Signal(action=SignalAction.HOLD, reason="holding long")


def build_bb_squeeze(params: dict) -> BBSqueezeV1:
    return BBSqueezeV1(
        squeeze_max=float(params.get("squeeze_max", 0.04)),
        stop_pct=float(params.get("stop_pct", 0.025)),
        target_band_mult=float(params.get("target_band_mult", 2.0)),
        min_adx=float(params.get("min_adx", 18.0)),
    )
