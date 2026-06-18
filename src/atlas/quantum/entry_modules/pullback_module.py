"""Módulo Pullback — retorno à EMA20 com rejeição."""
from __future__ import annotations

from atlas.quantum.candles import bullish_rejection_candle
from atlas.quantum.entry_modules.base_entry_module import BaseEntryModule, SignalResult
from atlas.quantum.models import EntryModule, MultiTimeframeContext, _val


class PullbackModule(BaseEntryModule):
    name = EntryModule.PULLBACK

    def evaluate(self, ctx: MultiTimeframeContext) -> SignalResult:
        candle = ctx.execution.candle
        ind = ctx.execution.indicators
        ema20 = _val(ind, "ema20")
        rsi = ind.rsi
        vol_sma = ind.volume_sma20

        if ema20 is None or rsi is None:
            return SignalResult.none(self.name, "EMA20/RSI indisponíveis")

        touched = candle.low <= ema20 * 1.005
        if not touched:
            return SignalResult.none(self.name, "preço não retornou à EMA20")

        if not (40 <= rsi <= 50):
            return SignalResult.none(self.name, f"RSI fora da zona de pullback ({rsi:.0f})")

        if vol_sma and candle.volume < vol_sma:
            return SignalResult.none(self.name, "volume abaixo da média")

        if not bullish_rejection_candle(candle, ema20):
            return SignalResult.none(self.name, "sem rejeição bullish na EMA20")

        confidence = 72.0
        if vol_sma and candle.volume >= vol_sma * 1.2:
            confidence += 10.0
        if 43 <= rsi <= 47:
            confidence += 8.0
        wick = ema20 - candle.low
        body = abs(candle.close - candle.open) or 0.01
        if wick / body >= 1.5:
            confidence += 10.0

        return SignalResult(
            triggered=True,
            module=self.name,
            confidence=min(100.0, confidence),
            reason="Preço retornou à EMA20 com rejeição e volume acima da média.",
            indicators=("EMA20", "RSI", "Volume"),
        )
