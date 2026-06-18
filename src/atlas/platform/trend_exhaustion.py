"""Trend Exhaustion Detector — evita entradas em possível exaustão."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ExhaustionResult:
    exhausted: bool
    score: float
    signals: list[str]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "exhausted": self.exhausted,
            "score": self.score,
            "signals": self.signals,
            "reason": self.reason,
        }


def detect_trend_exhaustion(row: pd.Series, *, candle_close: float | None = None) -> ExhaustionResult:
    """Detecta exaustão sem alterar o QuantumTrend Pro Core."""
    signals: list[str] = []
    score = 0.0
    close = candle_close if candle_close is not None else float(row.get("close", 0))

    adx = row.get("adx")
    prev_adx = row.get("prev_adx") if "prev_adx" in row.index else None
    if adx is not None and prev_adx is not None and adx < prev_adx and adx > 20:
        signals.append("ADX caindo")
        score += 25

    atr = row.get("atr")
    prev_atr = row.get("prev_atr") if "prev_atr" in row.index else None
    if atr is not None and prev_atr is not None and atr > prev_atr * 1.15:
        signals.append("ATR aumentando")
        score += 20

    rsi = row.get("rsi")
    if rsi is not None and rsi > 72:
        signals.append("momentum esticado (RSI alto)")
        score += 20

    ema20 = row.get("ema20")
    ema50 = row.get("ema50")
    if ema20 is not None and ema50 is not None and close > 0:
        dist = abs(close - ema20) / close
        if dist > 0.04:
            signals.append("distância excessiva da EMA20")
            score += 20
        if close > ema20 > ema50 and dist > 0.03:
            signals.append("preço esticado acima das médias")
            score += 15

    exhausted = score >= 45
    reason = "; ".join(signals) if signals else "sem sinais de exaustão"
    return ExhaustionResult(exhausted=exhausted, score=min(100, score), signals=signals, reason=reason)
