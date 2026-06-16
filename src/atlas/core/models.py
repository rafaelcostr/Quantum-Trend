from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TradingMode(str, Enum):
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class SignalAction(str, Enum):
    HOLD = "hold"
    ENTER_LONG = "enter_long"
    EXIT_LONG = "exit_long"


class Candle(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    model_config = {"frozen": True}


class IndicatorSnapshot(BaseModel):
    timestamp: datetime
    bb_upper: float | None = None
    bb_mid: float | None = None
    bb_lower: float | None = None
    rsi: float | None = None
    adx: float | None = None
    atr: float | None = None
    support: float | None = None
    resistance: float | None = None
    bb_width: float | None = None
    prev_bb_width: float | None = None
    mm20: float | None = None
    mm200: float | None = None
    prev_close: float | None = None
    mm200_daily: float | None = None
    daily_close: float | None = None
    macro_bull: bool | None = None
    extra: dict[str, float] = Field(default_factory=dict)

class Signal(BaseModel):
    action: SignalAction
    reason: str = ""
    stop_price: float | None = None
    target_price: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Order(BaseModel):
    symbol: str
    side: Side
    quantity: float
    order_type: str = "market"
    price: float | None = None
    stop_price: float | None = None
    client_order_id: str | None = None


class OrderResult(BaseModel):
    success: bool
    order_id: str | None = None
    filled_price: float | None = None
    filled_quantity: float | None = None
    fee: float = 0.0
    message: str = ""


class Position(BaseModel):
    symbol: str
    side: Side
    quantity: float
    entry_price: float
    entry_time: datetime
    stop_price: float | None = None
    target_price: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Trade(BaseModel):
    symbol: str
    side: Side
    entry_time: datetime
    entry_price: float
    exit_time: datetime | None = None
    exit_price: float | None = None
    quantity: float
    stop_price: float | None = None
    target_price: float | None = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    fees: float = 0.0
    strategy: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_closed(self) -> bool:
        return self.exit_time is not None and self.exit_price is not None


class PortfolioState(BaseModel):
    cash: float
    equity: float
    position: Position | None = None
    peak_equity: float = 0.0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
