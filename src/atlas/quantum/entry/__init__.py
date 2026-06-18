"""Módulos de entrada — herdam filtros do núcleo QuantumTrend."""
from __future__ import annotations

from dataclasses import dataclass

from atlas.core.models import Signal, SignalAction
from atlas.quantum.candles import bullish_rejection_candle
from atlas.quantum.models import EntryModule, MultiTimeframeContext, _val


@dataclass(frozen=True)
class EntrySignal:
    module: EntryModule
    signal: Signal


class PullbackEntry:
    name = EntryModule.PULLBACK

    def evaluate(self, ctx: MultiTimeframeContext) -> EntrySignal | None:
        if not ctx.macro_bull or not ctx.confirm_bull:
            return None
        candle = ctx.execution.candle
        ind = ctx.execution.indicators
        ema20 = _val(ind, "ema20")
        rsi = ind.rsi
        vol_sma = ind.volume_sma20
        if ema20 is None or rsi is None:
            return None
        touched = candle.low <= ema20 * 1.005
        if not touched:
            return None
        if not (40 <= rsi <= 50):
            return None
        if vol_sma and candle.volume < vol_sma:
            return None
        if not bullish_rejection_candle(candle, ema20):
            return None
        return EntrySignal(
            module=self.name,
            signal=Signal(
                action=SignalAction.ENTER_LONG,
                reason="pullback: retorno à EMA20 com rejeição de alta",
                metadata={"entry_module": self.name.value},
            ),
        )


class BreakoutEntry:
    name = EntryModule.BREAKOUT

    def evaluate(self, ctx: MultiTimeframeContext) -> EntrySignal | None:
        if not ctx.macro_bull or not ctx.confirm_bull:
            return None
        candle = ctx.execution.candle
        ind = ctx.execution.indicators
        high_20 = ind.high_20
        vol_sma = ind.volume_sma20
        if high_20 is None:
            return None
        if candle.close <= high_20:
            return None
        if vol_sma and candle.volume < vol_sma:
            return None
        return EntrySignal(
            module=self.name,
            signal=Signal(
                action=SignalAction.ENTER_LONG,
                reason="breakout: rompimento da máxima de 20 candles",
                metadata={"entry_module": self.name.value},
            ),
        )


class SupertrendEntry:
    name = EntryModule.SUPERTREND

    def evaluate(self, ctx: MultiTimeframeContext) -> EntrySignal | None:
        if not ctx.macro_bull:
            return None
        candle = ctx.execution.candle
        ind = ctx.execution.indicators
        ema200 = _val(ind, "ema200")
        adx = ind.adx
        st_dir = ind.supertrend_dir
        if ema200 is None or adx is None or st_dir is None:
            return None
        if candle.close <= ema200:
            return None
        if adx <= 20:
            return None
        if st_dir < 0:
            return None
        return EntrySignal(
            module=self.name,
            signal=Signal(
                action=SignalAction.ENTER_LONG,
                reason="supertrend: tendência de compra com ADX e EMA200",
                metadata={"entry_module": self.name.value},
            ),
        )


ENTRY_MODULES: dict[EntryModule, object] = {
    EntryModule.PULLBACK: PullbackEntry(),
    EntryModule.BREAKOUT: BreakoutEntry(),
    EntryModule.SUPERTREND: SupertrendEntry(),
}


def evaluate_entry(ctx: MultiTimeframeContext, module: EntryModule) -> EntrySignal | None:
    if module == EntryModule.AUTO:
        for key in (EntryModule.PULLBACK, EntryModule.BREAKOUT, EntryModule.SUPERTREND):
            result = evaluate_entry(ctx, key)
            if result is not None:
                return result
        return None
    handler = ENTRY_MODULES.get(module)
    if handler is None:
        return None
    return handler.evaluate(ctx)
