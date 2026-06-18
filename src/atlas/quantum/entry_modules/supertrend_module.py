"""Módulo Supertrend — tendência de compra com filtro EMA200 + ADX."""
from __future__ import annotations

from atlas.quantum.entry_modules.base_entry_module import BaseEntryModule, SignalResult
from atlas.quantum.models import EntryModule, MultiTimeframeContext, _val


class SupertrendModule(BaseEntryModule):
    name = EntryModule.SUPERTREND

    def evaluate(self, ctx: MultiTimeframeContext) -> SignalResult:
        candle = ctx.execution.candle
        ind = ctx.execution.indicators
        ema200 = _val(ind, "ema200")
        adx = ind.adx
        st_dir = ind.supertrend_dir
        supertrend = ind.supertrend

        if ema200 is None or adx is None or st_dir is None:
            return SignalResult.none(self.name, "indicadores Supertrend/EMA200 indisponíveis")

        if candle.close <= ema200:
            return SignalResult.none(self.name, "preço abaixo da EMA200")

        if adx <= 20:
            return SignalResult.none(self.name, f"ADX insuficiente ({adx:.1f})")

        if st_dir < 0:
            return SignalResult.none(self.name, "Supertrend bearish")

        if supertrend is not None and candle.close <= supertrend:
            return SignalResult.none(self.name, "fechamento abaixo da linha Supertrend")

        confidence = 74.0
        if adx >= 30:
            confidence += 12.0
        elif adx >= 25:
            confidence += 8.0
        if ema200 > 0:
            dist = (candle.close - ema200) / ema200
            if dist >= 0.02:
                confidence += 6.0
        if ctx.macro_bull:
            confidence += 5.0

        return SignalResult(
            triggered=True,
            module=self.name,
            confidence=min(100.0, confidence),
            reason="Supertrend bullish com preço acima da EMA200 e ADX confirmando tendência.",
            indicators=("Supertrend", "EMA200", "ADX"),
        )
