from __future__ import annotations

from typing import Protocol

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal


class Strategy(Protocol):
    """Pure signal logic — no broker or database access."""

    name: str

    def evaluate(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position | None,
    ) -> Signal: ...
