from __future__ import annotations

from typing import Protocol

from atlas.core.models import Candle, Order, OrderResult, Position


class Broker(Protocol):
    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> list[Candle]: ...

    def get_balance(self) -> float: ...

    def get_position(self, symbol: str) -> Position | None: ...

    def place_order(self, order: Order) -> OrderResult: ...

    def cancel_order(self, order_id: str) -> bool: ...
