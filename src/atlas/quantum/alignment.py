"""Alignment Score Engine — score quantitativo de 0 a 100."""
from __future__ import annotations

from dataclasses import dataclass

from atlas.quantum.models import MultiTimeframeContext, RiskProfile, SCORE_THRESHOLD, _val
from atlas.quantum.regime import MarketRegimeEngine


@dataclass(frozen=True)
class AlignmentScoreResult:
    total: float
    breakdown: dict[str, float]
    eligible: bool
    threshold: int
    reason: str


class AlignmentScoreEngine:
    """
    Componentes:
    - Trend Alignment: 35
    - ADX Strength: 20
    - Volume Confirmation: 15
    - Volatility Regime: 15
    - Momentum Confirmation: 15
    """

    WEIGHTS = {
        "trend_alignment": 35.0,
        "adx_strength": 20.0,
        "volume_confirmation": 15.0,
        "volatility_regime": 15.0,
        "momentum_confirmation": 15.0,
    }

    def __init__(
        self,
        *,
        risk_profile: RiskProfile = RiskProfile.MODERATE,
        regime_engine: MarketRegimeEngine | None = None,
    ) -> None:
        self.risk_profile = risk_profile
        self.regime_engine = regime_engine or MarketRegimeEngine()

    @property
    def threshold(self) -> int:
        return SCORE_THRESHOLD[self.risk_profile]

    def score(self, ctx: MultiTimeframeContext, *, entry_signal: bool) -> AlignmentScoreResult:
        breakdown: dict[str, float] = {}

        trend = 0.0
        if ctx.macro_bull:
            trend += 20.0
        if ctx.confirm_bull:
            trend += 15.0
        breakdown["trend_alignment"] = min(self.WEIGHTS["trend_alignment"], trend)

        adx_pts = 0.0
        macro_adx = ctx.macro.indicators.adx if ctx.macro else None
        exec_adx = ctx.execution.indicators.adx
        ref_adx = macro_adx if macro_adx is not None else exec_adx
        if ref_adx is not None:
            if ref_adx >= 30:
                adx_pts = 20.0
            elif ref_adx >= 25:
                adx_pts = 16.0
            elif ref_adx >= 20:
                adx_pts = 12.0
            elif ref_adx >= 15:
                adx_pts = 6.0
        breakdown["adx_strength"] = adx_pts

        volume_pts = 0.0
        vol = ctx.execution.candle.volume
        vol_sma = ctx.execution.indicators.volume_sma20
        if vol_sma and vol_sma > 0 and vol >= vol_sma:
            ratio = vol / vol_sma
            volume_pts = 15.0 if ratio >= 1.2 else 10.0 if ratio >= 1.0 else 5.0
        breakdown["volume_confirmation"] = volume_pts

        vol_regime_pts = 0.0
        atr = ctx.execution.indicators.atr
        close = ctx.execution.candle.close
        if atr and close > 0:
            atr_pct = atr / close
            if 0.008 <= atr_pct <= 0.035:
                vol_regime_pts = 15.0
            elif atr_pct < 0.008:
                vol_regime_pts = 8.0
            elif atr_pct <= 0.045:
                vol_regime_pts = 6.0
        breakdown["volatility_regime"] = vol_regime_pts

        momentum_pts = 0.0
        rsi = ctx.execution.indicators.rsi
        ema20 = _val(ctx.execution.indicators, "ema20")
        if entry_signal and rsi is not None and ema20 is not None:
            if ctx.execution.candle.close > ema20 and 45 <= rsi <= 65:
                momentum_pts = 15.0
            elif ctx.execution.candle.close > ema20:
                momentum_pts = 8.0
        breakdown["momentum_confirmation"] = momentum_pts

        total = round(sum(breakdown.values()), 1)
        eligible = total >= self.threshold
        reason = "score aprovado" if eligible else f"score abaixo de {self.threshold}"
        return AlignmentScoreResult(
            total=total,
            breakdown=breakdown,
            eligible=eligible,
            threshold=self.threshold,
            reason=reason,
        )
