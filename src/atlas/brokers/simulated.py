from __future__ import annotations

from dataclasses import dataclass, field

from atlas.core.models import Candle, ExecutionConfig, Order, OrderResult, Position, Side


@dataclass
class SimulatedBroker:
    symbol: str
    execution: ExecutionConfig
    candles: list[Candle] = field(default_factory=list)
    _cursor: int = 0
    cash: float = 10_000.0
    position: Position | None = None
    _pending_entry: dict | None = field(default=None, init=False)

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
        return self.position if self.position and self.position.symbol == symbol else None

    def _apply_slippage(self, price: float, side: Side) -> float:
        slip = self.execution.slippage_rate
        if side == Side.BUY:
            return price * (1 + slip)
        return price * (1 - slip)

    def _fee(self, notional: float) -> float:
        return notional * self.execution.fee_rate

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
        price = self._apply_slippage(candle.close, order.side)
        notional = price * order.quantity
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
                    filled_quantity=order.quantity,
                    fee=fee,
                )
            cost = notional + fee
            if cost > self.cash:
                return OrderResult(success=False, message="insufficient cash")
            self.cash -= cost
            self.position = Position(
                symbol=order.symbol,
                side=Side.BUY,
                quantity=order.quantity,
                entry_price=price,
                entry_time=candle.timestamp,
                stop_price=order.stop_price,
                target_price=None,
            )
            return OrderResult(
                success=True,
                order_id=f"sim-{self._cursor}",
                filled_price=price,
                filled_quantity=order.quantity,
                fee=fee,
            )
        if order.side == Side.SHORT:
            proceeds = notional - fee
            self.cash += proceeds
            self.position = Position(
                symbol=order.symbol,
                side=Side.SHORT,
                quantity=order.quantity,
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
                filled_quantity=order.quantity,
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
            filled_quantity=order.quantity,
            fee=fee,
        )

    def execute_pending_at_open(self, candle: Candle) -> OrderResult | None:
        if not self._pending_entry:
            return None
        pending = self._pending_entry
        self._pending_entry = None
        price = self._apply_slippage(candle.open, Side.BUY)
        qty = pending["quantity"]
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

    def equity(self, mark_price: float) -> float:
        if self.position:
            if self.position.side == Side.SHORT or self.position.metadata.get("position_kind") == "short":
                return self.cash + (self.position.entry_price - mark_price) * self.position.quantity
            return self.cash + self.position.quantity * mark_price
        return self.cash
