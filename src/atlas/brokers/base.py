from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from atlas.core.models import Candle, Order, OrderResult, Position
from atlas.core.symbols import NormalizedSymbol, normalize_symbol


class ExchangeId(str, Enum):
    BINANCE = "binance"
    SIMULATED = "simulated"
    BYBIT = "bybit"
    OKX = "okx"
    COINBASE = "coinbase"


class MarketType(str, Enum):
    SPOT = "spot"
    FUTURES = "futures"


class BrokerVenue(str, Enum):
    PAPER_LOCAL = "paper_local"
    DEMO_EXCHANGE = "demo_exchange"
    LIVE_EXCHANGE = "live_exchange"


@dataclass(frozen=True)
class MarketSpec:
    symbol: NormalizedSymbol
    exchange_id: str
    market_type: MarketType = MarketType.SPOT
    venue: BrokerVenue = BrokerVenue.DEMO_EXCHANGE
    price_precision: int | None = None
    quantity_precision: int | None = None
    min_qty: float = 0.0
    min_notional: float = 0.0
    quantity_step: float = 0.0

    @property
    def canonical_symbol(self) -> str:
        return self.symbol.canonical

    @property
    def exchange_symbol(self) -> str:
        return self.symbol.exchange

    @property
    def compact_symbol(self) -> str:
        return self.symbol.compact


@dataclass(frozen=True)
class BrokerCapabilities:
    exchange_id: str
    market_types: tuple[MarketType, ...]
    venues: tuple[BrokerVenue, ...]
    supports_client_order_id: bool = True
    supports_fetch_open_orders: bool = False
    supports_exchange_stops: bool = False


def market_spec(
    symbol: str,
    *,
    exchange_id: str = ExchangeId.BINANCE.value,
    market_type: str | MarketType = MarketType.SPOT,
    venue: str | BrokerVenue = BrokerVenue.DEMO_EXCHANGE,
    price_precision: int | None = None,
    quantity_precision: int | None = None,
    min_qty: float = 0.0,
    min_notional: float = 0.0,
    quantity_step: float = 0.0,
) -> MarketSpec:
    mt = market_type if isinstance(market_type, MarketType) else MarketType(str(market_type or "spot"))
    vn = venue if isinstance(venue, BrokerVenue) else BrokerVenue(str(venue or "demo_exchange"))
    return MarketSpec(
        symbol=normalize_symbol(symbol),
        exchange_id=str(exchange_id or ExchangeId.BINANCE.value).lower(),
        market_type=mt,
        venue=vn,
        price_precision=price_precision,
        quantity_precision=quantity_precision,
        min_qty=float(min_qty or 0),
        min_notional=float(min_notional or 0),
        quantity_step=float(quantity_step or 0),
    )


class Broker(Protocol):
    spec: MarketSpec
    capabilities: BrokerCapabilities

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> list[Candle]: ...

    def get_balance(self) -> float: ...

    def get_position(self, symbol: str) -> Position | None: ...

    def place_order(self, order: Order) -> OrderResult: ...

    def cancel_order(self, order_id: str) -> bool: ...

    def market_spec(self, symbol: str | None = None) -> MarketSpec: ...
