"""Market Regime Engine — classificação automática do mercado."""
from __future__ import annotations

from dataclasses import dataclass

from atlas.quantum.models import MarketRegime, MultiTimeframeContext, _val


@dataclass
class RegimeResult:
    regime: MarketRegime
    reason: str
    adx: float | None = None
    atr_pct: float | None = None
    ema_slope: float | None = None


class MarketRegimeEngine:
    """Detecta regime usando EMA, ADX, ATR e inclinação das médias."""

    def __init__(
        self,
        *,
        adx_trend_min: float = 20.0,
        adx_weak_min: float = 15.0,
        high_vol_atr_pct: float = 0.045,
    ) -> None:
        self.adx_trend_min = adx_trend_min
        self.adx_weak_min = adx_weak_min
        self.high_vol_atr_pct = high_vol_atr_pct

    def classify(self, ctx: MultiTimeframeContext) -> RegimeResult:
        macro = ctx.macro or ctx.execution
        ind = macro.indicators
        candle = macro.candle

        ema50 = _val(ind, "ema50") or _val(ind, "ema20")
        ema200 = _val(ind, "ema200")
        adx = ind.adx
        atr = ind.atr

        if ema50 is None or ema200 is None or adx is None:
            return RegimeResult(MarketRegime.RANGE, "indicadores macro incompletos")

        atr_pct = (atr / candle.close) if atr and candle.close > 0 else None
        if atr_pct is not None and atr_pct >= self.high_vol_atr_pct:
            return RegimeResult(
                MarketRegime.HIGH_VOLATILITY,
                f"ATR elevado ({atr_pct:.2%})",
                adx=adx,
                atr_pct=atr_pct,
            )

        ema_slope = (ema50 - ema200) / ema200 if ema200 else 0.0
        bullish = ema50 > ema200
        bearish = ema50 < ema200

        if adx < self.adx_weak_min:
            return RegimeResult(
                MarketRegime.RANGE,
                f"ADX baixo ({adx:.1f}) — mercado lateral",
                adx=adx,
                ema_slope=ema_slope,
            )

        if bullish and adx >= self.adx_trend_min:
            if ema_slope >= 0.03:
                return RegimeResult(
                    MarketRegime.BULL_TREND,
                    "EMA50 > EMA200 com ADX forte",
                    adx=adx,
                    ema_slope=ema_slope,
                )
            return RegimeResult(
                MarketRegime.WEAK_BULL,
                "EMA50 > EMA200 com ADX moderado",
                adx=adx,
                ema_slope=ema_slope,
            )

        if bearish and adx >= self.adx_trend_min:
            if ema_slope <= -0.03:
                return RegimeResult(
                    MarketRegime.BEAR_TREND,
                    "EMA50 < EMA200 com ADX forte",
                    adx=adx,
                    ema_slope=ema_slope,
                )
            return RegimeResult(
                MarketRegime.WEAK_BEAR,
                "EMA50 < EMA200 com ADX moderado",
                adx=adx,
                ema_slope=ema_slope,
            )

        return RegimeResult(
            MarketRegime.RANGE,
            "condições mistas entre médias e ADX",
            adx=adx,
            ema_slope=ema_slope,
        )

    def allows_long(self, regime: MarketRegime) -> bool:
        return regime in {MarketRegime.BULL_TREND, MarketRegime.WEAK_BULL}
