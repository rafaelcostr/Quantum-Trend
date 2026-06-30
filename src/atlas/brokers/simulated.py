from __future__ import annotations

from dataclasses import dataclass, field
from math import floor

from atlas.brokers.base import BrokerCapabilities, BrokerVenue, ExchangeId, MarketSpec, MarketType, market_spec
from atlas.core.models import Candle, ExecutionConfig, Order, OrderResult, Position, Side
from atlas.core.symbols import normalize_symbol


@dataclass
class SimulatedBroker:
    symbol: str
    execution: ExecutionConfig
    candles: list[Candle] = field(default_factory=list)
    market_type: str = MarketType.SPOT.value
    venue: str = BrokerVenue.PAPER_LOCAL.value
    _cursor: int = 0
    cash: float = 10_000.0
    position: Position | None = None
    _pending_entry: dict | None = field(default=None, init=False)
    spec: MarketSpec = field(init=False)
    capabilities: BrokerCapabilities = field(init=False)

    def __post_init__(self) -> None:
        sym = normalize_symbol(self.symbol)
        self.symbol = sym.canonical
        self.spec = market_spec(
            self.symbol,
            exchange_id=ExchangeId.SIMULATED.value,
            market_type=self.market_type,
            venue=self.venue,
            min_notional=self.execution.min_order_notional,
            quantity_step=self.execution.quantity_step,
        )
        self.capabilities = BrokerCapabilities(
            exchange_id=ExchangeId.SIMULATED.value,
            market_types=(MarketType.SPOT, MarketType.FUTURES),
            venues=(BrokerVenue.PAPER_LOCAL,),
            supports_client_order_id=True,
            supports_fetch_open_orders=True,
        )

    def set_candles(self, candles: list[Candle]) -> None:
        self.candles = candles
        self._cursor = 0

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> list[Candle]:
        end = self._cursor
        start = max(0, end - limit)
        return self.candles[start:end]

    def get_balance(self) -> float:
        return self.cash

    def get_position(self, symbol: str) -> Position | None:
        canonical = normalize_symbol(symbol).canonical
        return self.position if self.position and normalize_symbol(self.position.symbol).canonical == canonical else None

    def _apply_slippage(self, price: float, side: Side) -> float:
        slip = self.execution.slippage_rate
        if self.execution.liquidity_notional and self.execution.liquidity_notional > 0:
            # Impacto simples de liquidez: ordens grandes pagam mais slippage.
            slip += min(0.02, price / self.execution.liquidity_notional)
        slip += max(self.execution.spread_rate, 0.0) / 2
        if side == Side.BUY:
            return price * (1 + slip)
        return price * (1 - slip)

    def _fee(self, notional: float) -> float:
        taker_fee = self.execution.taker_fee_rate
        return notional * (taker_fee if taker_fee is not None else self.execution.fee_rate)

    def _rounded_quantity(self, quantity: float) -> float:
        step = self.execution.quantity_step or self.spec.quantity_step
        if step and step > 0:
            return floor(quantity / step) * step
        return quantity

    def _validate_notional(self, price: float, quantity: float) -> OrderResult | None:
        if quantity <= 0:
            return OrderResult(success=False, message="quantity rounded to zero")
        min_notional = self.execution.min_order_notional or self.spec.min_notional
        if min_notional and price * quantity < min_notional:
            return OrderResult(success=False, message="below minimum order notional")
        return None

    def market_spec(self, symbol: str | None = None) -> MarketSpec:
        if not symbol or normalize_symbol(symbol).canonical == self.symbol:
            return self.spec
        return market_spec(
            symbol,
            exchange_id=ExchangeId.SIMULATED.value,
            market_type=self.market_type,
            venue=self.venue,
            min_notional=self.execution.min_order_notional,
            quantity_step=self.execution.quantity_step,
        )

    def queue_entry_next_open(
        self,
        quantity: float,
        stop: float | None,
        target: float | None,
        metadata: dict | None = None,
    ) -> None:
        self._pending_entry = {
            "quantity": quantity,
            "stop": stop,
            "target": target,
            "metadata": metadata or {},
        }

    def place_order(self, order: Order) -> OrderResult:
        if not self.candles or self._cursor == 0:
            return OrderResult(success=False, message="no candle context")
        candle = self.candles[self._cursor - 1]
        quantity = self._rounded_quantity(order.quantity)
        price = self._apply_slippage(candle.close, order.side)
        invalid = self._validate_notional(price, quantity)
        if invalid:
            return invalid
        notional = price * quantity
        fee = self._fee(notional)
        if order.side == Side.BUY:
            if self.position is not None and (
                self.position.side == Side.SHORT or self.position.metadata.get("position_kind") == "short"
            ):
                cost = notional + fee
                self.cash -= cost
                self.position = None
                return OrderResult(
                    success=True,
                    order_id=f"sim-cover-{self._cursor}",
                    filled_price=price,
                    filled_quantity=quantity,
                    fee=fee,
                )
            cost = notional + fee
            if cost > self.cash:
                return OrderResult(success=False, message="insufficient cash")
            self.cash -= cost
            self.position = Position(
                symbol=order.symbol,
                side=Side.BUY,
                quantity=quantity,
                entry_price=price,
                entry_time=candle.timestamp,
                stop_price=order.stop_price,
                target_price=None,
            )
            return OrderResult(
                success=True,
                order_id=f"sim-{self._cursor}",
                filled_price=price,
                filled_quantity=quantity,
                fee=fee,
            )
        if order.side == Side.SHORT:
            proceeds = notional - fee
            self.cash += proceeds
            self.position = Position(
                symbol=order.symbol,
                side=Side.SHORT,
                quantity=quantity,
                entry_price=price,
                entry_time=candle.timestamp,
                stop_price=order.stop_price,
                target_price=None,
                metadata={"position_kind": "short"},
            )
            return OrderResult(
                success=True,
                order_id=f"sim-short-{self._cursor}",
                filled_price=price,
                filled_quantity=quantity,
                fee=fee,
            )
        if self.position is None:
            return OrderResult(success=False, message="no position to close")
        proceeds = notional - fee
        self.cash += proceeds
        self.position = None
        return OrderResult(
            success=True,
            order_id=f"sim-{self._cursor}",
            filled_price=price,
            filled_quantity=quantity,
            fee=fee,
        )

    def execute_pending_at_open(self, candle: Candle) -> OrderResult | None:
        if not self._pending_entry:
            return None
        pending = self._pending_entry
        self._pending_entry = None
        price = self._apply_slippage(candle.open, Side.BUY)
        qty = self._rounded_quantity(pending["quantity"])
        invalid = self._validate_notional(price, qty)
        if invalid:
            return invalid
        notional = price * qty
        fee = self._fee(notional)
        cost = notional + fee
        if cost > self.cash:
            return OrderResult(success=False, message="insufficient cash at open")
        self.cash -= cost
        self.position = Position(
            symbol=self.symbol,
            side=Side.BUY,
            quantity=qty,
            entry_price=price,
            entry_time=candle.timestamp,
            stop_price=pending["stop"],
            target_price=pending["target"],
            metadata=pending.get("metadata", {}),
        )
        return OrderResult(success=True, filled_price=price, filled_quantity=qty, fee=fee)

    def cancel_order(self, order_id: str) -> bool:
        return True

    def fetch_open_orders(self, symbol: str) -> list[dict]:
        return []

    def equity(self, mark_price: float) -> float:
        if self.position:
            if self.position.side == Side.SHORT or self.position.metadata.get("position_kind") == "short":
                return self.cash + (self.position.entry_price - mark_price) * self.position.quantity
            return self.cash + self.position.quantity * mark_price
        return self.cash
