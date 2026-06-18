"""Módulo Breakout — rompimento da máxima de 20 candles."""
from __future__ import annotations

from atlas.quantum.entry_modules.base_entry_module import BaseEntryModule, SignalResult
from atlas.quantum.models import EntryModule, MultiTimeframeContext


class BreakoutModule(BaseEntryModule):
    name = EntryModule.BREAKOUT

    def evaluate(self, ctx: MultiTimeframeContext) -> SignalResult:
        candle = ctx.execution.candle
        ind = ctx.execution.indicators
        high_20 = ind.high_20
        vol_sma = ind.volume_sma20
        adx = ind.adx

        if high_20 is None:
            return SignalResult.none(self.name, "lookback high20 indisponível")

        if candle.close <= high_20:
            return SignalResult.none(self.name, "sem rompimento acima da máxima de 20 candles")

        if vol_sma and candle.volume < vol_sma:
            return SignalResult.none(self.name, "volume abaixo da média")

        if adx is not None and adx < 15:
            return SignalResult.none(self.name, f"ADX insuficiente ({adx:.1f})")

        confidence = 75.0
        if vol_sma and vol_sma > 0:
            ratio = candle.volume / vol_sma
            if ratio >= 1.5:
                confidence += 12.0
            elif ratio >= 1.2:
                confidence += 8.0
        if adx is not None:
            if adx >= 30:
                confidence += 10.0
            elif adx >= 22:
                confidence += 5.0
        extension = (candle.close - high_20) / high_20 if high_20 > 0 else 0
        if extension >= 0.003:
            confidence += 6.0

        return SignalResult(
            triggered=True,
            module=self.name,
            confidence=min(100.0, confidence),
            reason="Rompimento da máxima de 20 candles com confirmação de volume.",
            indicators=("High20", "Volume", "ADX"),
        )
