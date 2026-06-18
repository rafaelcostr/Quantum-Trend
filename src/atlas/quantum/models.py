"""Modelos compartilhados do QuantumTrend Pro Core."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from atlas.core.models import Candle, IndicatorSnapshot


class MarketRegime(str, Enum):
    BULL_TREND = "bull_trend"
    WEAK_BULL = "weak_bull"
    RANGE = "range"
    WEAK_BEAR = "weak_bear"
    BEAR_TREND = "bear_trend"
    HIGH_VOLATILITY = "high_volatility"


class RiskProfile(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class EntryModule(str, Enum):
    PULLBACK = "pullback"
    BREAKOUT = "breakout"
    SUPERTREND = "supertrend"
    AUTO = "auto"


REGIME_LABELS: dict[MarketRegime, str] = {
    MarketRegime.BULL_TREND: "Tendência de Alta",
    MarketRegime.WEAK_BULL: "Alta Fraca",
    MarketRegime.RANGE: "Lateral",
    MarketRegime.WEAK_BEAR: "Baixa Fraca",
    MarketRegime.BEAR_TREND: "Tendência de Baixa",
    MarketRegime.HIGH_VOLATILITY: "Alta Volatilidade",
}

SCORE_THRESHOLD: dict[RiskProfile, int] = {
    RiskProfile.CONSERVATIVE: 90,
    RiskProfile.MODERATE: 80,
    RiskProfile.AGGRESSIVE: 70,
}

# Regimes recomendados por módulo de entrada (long only)
ENTRY_REGIME_AFFINITY: dict[EntryModule, set[MarketRegime]] = {
    EntryModule.PULLBACK: {MarketRegime.BULL_TREND, MarketRegime.WEAK_BULL},
    EntryModule.BREAKOUT: {MarketRegime.BULL_TREND, MarketRegime.WEAK_BULL},
    EntryModule.SUPERTREND: {MarketRegime.BULL_TREND, MarketRegime.WEAK_BULL, MarketRegime.WEAK_BEAR},
}


@dataclass(frozen=True)
class TimeframeSnapshot:
    timeframe: str
    candle: Candle
    indicators: IndicatorSnapshot


@dataclass
class MultiTimeframeContext:
    """Contexto sincronizado nos três timeframes operacionais."""

    execution: TimeframeSnapshot
    confirm: TimeframeSnapshot | None = None
    macro: TimeframeSnapshot | None = None
    regime: MarketRegime = MarketRegime.RANGE
    alignment_score: float = 0.0
    alignment_breakdown: dict[str, float] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def macro_bull(self) -> bool:
        macro = self.macro
        if macro is None:
            return False
        ema50 = _val(macro.indicators, "ema50")
        ema200 = _val(macro.indicators, "ema200")
        adx = macro.indicators.adx
        if ema50 is None or ema200 is None or adx is None:
            return False
        return ema50 > ema200 and adx > 20

    @property
    def confirm_bull(self) -> bool:
        confirm = self.confirm
        if confirm is None:
            return False
        ema20 = _val(confirm.indicators, "ema20")
        ema50 = _val(confirm.indicators, "ema50")
        if ema20 is None or ema50 is None:
            return False
        return ema20 > ema50 and confirm.candle.close > ema20

    @property
    def atr_execution(self) -> float | None:
        return self.execution.indicators.atr


def _val(indicators: IndicatorSnapshot, key: str) -> float | None:
    value = getattr(indicators, key, None)
    if value is not None:
        return float(value)
    extra = indicators.extra or {}
    raw = extra.get(key)
    return float(raw) if raw is not None else None