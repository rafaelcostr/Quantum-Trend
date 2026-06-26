"""Orquestrador de regime — ativa Bull ou Bear, nunca ambos no mesmo ativo."""
from __future__ import annotations

from atlas.core.models import Candle, IndicatorSnapshot, Signal, SignalAction
from atlas.strategies.metadata import get_market_type, is_bear_strategy, is_bull_entry_module, is_range_strategy

MarketRegimeKind = str  # bull | bear | range


def detect_execution_regime(candle: Candle, indicators: IndicatorSnapshot) -> MarketRegimeKind:
    """Classifica regime operacional a partir do timeframe de execução."""
    if indicators.ema200 is None or indicators.adx is None:
        return "range"

    adx = float(indicators.adx)
    if adx < 15:
        return "range"

    if candle.close > indicators.ema200 and adx >= 20:
        return "bull"

    if candle.close < indicators.ema200 and adx >= 20:
        return "bear"

    return "range"


def regime_allows_market_type(regime: MarketRegimeKind, market_type: str) -> bool:
    if market_type == "bull":
        return regime == "bull"
    if market_type == "bear":
        return regime == "bear"
    if market_type == "range":
        return regime == "range"
    return True


def gate_strategy_by_regime(
    strategy_name: str,
    candle: Candle,
    indicators: IndicatorSnapshot,
) -> Signal | None:
    """
    Retorna Signal HOLD se a estratégia não pertence ao regime atual.
    None = prosseguir com evaluate normal.
    """
    market_type = get_market_type(strategy_name)
    regime = detect_execution_regime(candle, indicators)
    if regime_allows_market_type(regime, market_type):
        return None
    label = {"bull": "Bull", "bear": "Bear", "range": "Range"}.get(market_type, market_type)
    return Signal(
        action=SignalAction.HOLD,
        reason=f"regime gate: {label} strategy disabled in {regime} market",
        metadata={"regime_gate": regime, "market_type": market_type},
    )


def validate_slot_market_mix(items: list[str] | list) -> None:
    """Impede bull + bear habilitados no mesmo ativo (BTC ou ETH)."""
    if not items:
        return
    first = items[0]
    if hasattr(first, "strategy") and hasattr(first, "base") and hasattr(first, "enabled"):
        from atlas.core.symbols import OPERATED_BASES

        for base in OPERATED_BASES:
            names = [s.strategy for s in items if s.enabled and str(s.base).upper() == base]
            _validate_bull_bear_mix(names, base)
        return
    _validate_bull_bear_mix([str(n) for n in items], None)


def _validate_bull_bear_mix(strategy_names: list[str], base: str | None) -> None:
    types = {get_market_type(n) for n in strategy_names}
    if "bull" in types and "bear" in types:
        suffix = f" em {base}" if base else " no mesmo bot"
        raise ValueError(
            f"Estratégias Bull e Bear não podem operar simultaneamente{suffix} — "
            "habilite apenas um módulo de mercado por ativo."
        )


def categorize_strategy_name(name: str) -> str:
    if is_bear_strategy(name):
        return "bear"
    if is_range_strategy(name):
        return "range"
    if is_bull_entry_module(name) or get_market_type(name) == "bull":
        return "bull"
    return get_market_type(name)
