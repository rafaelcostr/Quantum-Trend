"""Utilitários de candles e rejeição."""
from __future__ import annotations

from atlas.core.models import Candle


def bullish_rejection_candle(candle: Candle, ema20: float) -> bool:
    """
    Candle de rejeição de alta:
    - fechamento acima da EMA20;
    - sombra inferior maior que o corpo;
    - fechamento no terço superior do candle.
    """
    if candle.close <= ema20:
        return False
    body = abs(candle.close - candle.open)
    if body <= 0:
        return False
    lower_shadow = min(candle.open, candle.close) - candle.low
    if lower_shadow <= body:
        return False
    span = candle.high - candle.low
    if span <= 0:
        return False
    close_position = (candle.close - candle.low) / span
    return close_position >= 0.66
