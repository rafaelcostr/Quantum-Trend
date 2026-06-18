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
    LONG = "LONG"  # compat UI


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
    ema20: float | None = None
    ema50: float | None = None
    ema200: float | None = None
    prev_ema20: float | None = None
    high_20: float | None = None
    low_20: float | None = None
    volume_sma20: float | None = None
    supertrend: float | None = None
    supertrend_dir: float | None = None
    prev_supertrend_dir: float | None = None
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
    current_price: float = 0.0
    strategy: str = ""

    @property
    def pnl(self) -> float:
        if self.side in (Side.BUY, Side.LONG):
            return (self.current_price - self.entry_price) * self.quantity
        return (self.entry_price - self.current_price) * self.quantity

    @property
    def pnl_pct(self) -> float:
        if self.entry_price <= 0:
            return 0.0
        if self.side in (Side.BUY, Side.LONG):
            return (self.current_price / self.entry_price - 1) * 100
        return (1 - self.current_price / self.entry_price) * 100


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


class ExchangeConfig(BaseModel):
    id: str = "binance"
    symbol: str = "BTC/USDT"
    timeframe: str = "4h"
    quote_asset: str = "USDT"
    demo: bool = False
    limit: int = 500


class StrategyConfig(BaseModel):
    name: str = "mm200_trend_v2"
    params: dict[str, Any] = Field(default_factory=dict)


class RiskConfig(BaseModel):
    initial_capital: float = 10_000.0
    risk_per_trade: float = 0.01
    max_open_positions: int = 1
    max_daily_drawdown: float = 0.03
    max_weekly_drawdown: float = 0.08
    sizing_mode: str = "risk_based"
    max_drawdown_pct: float = 0.25
    daily_loss_pct: float = 0.05
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04


class ExecutionConfig(BaseModel):
    fee_rate: float = 0.001
    slippage_rate: float = 0.0005
    entry_on_next_open: bool = True
    use_exchange_stop: bool = False
    initial_capital: float = 10_000.0
    max_position_pct: float = 0.95


class DataConfig(BaseModel):
    years: int = 3  # 0 = todo historico disponivel na exchange (ex.: BTC/USDT desde ~2017)
    cache_dir: str = "data/cache"


class RuntimeConfig(BaseModel):
    poll_seconds: int = 60
    reconcile_minutes: int = 15
    alert_on_signal: bool = True
    drawdown_alert_pct: float = 0.10


class AtlasConfig(BaseModel):
    mode: TradingMode = TradingMode.PAPER
    exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    database_url: str = "postgresql://atlas:atlas@localhost:15432/atlas_quant"


# --- DTOs para API / React ---


class BacktestMetrics(BaseModel):
    total_return_pct: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe: float
    win_rate_pct: float
    trades: int
    expectancy: float
    atlas_score: float = 0.0


class JournalEntry(BaseModel):
    date: str
    asset: str
    entry: float
    exit: float
    pnl: float
    strategy: str
    side: Side = Side.BUY


class MarketTicker(BaseModel):
    symbol: str
    price: float
    change_pct: float
    volume_24h: float = 0.0
    sparkline: list[float] = Field(default_factory=list)


class PositionDTO(BaseModel):
    asset: str
    side: str
    entry: float
    current: float
    pnl: float
    pnl_pct: float
    strategy: str
    color: str = "#7C3AED"


class StrategyDTO(BaseModel):
    name: str
    winrate: float
    pf: float
    dd: float
    status: str
    id: str = ""


class DashboardStats(BaseModel):
    balance: float
    balance_delta_pct: float
    pnl: float
    pnl_delta_pct: float
    active_strategy: str
    win_rate_pct: float
    profit_factor: float
    trades_today: int
    atlas_score: int
    bot_running: bool
    bot_mode: str = "paper"
    kill_switch: bool
    balance_source: str = "unknown"
    account_label: str = "—"
    alignment_score: float = 0.0
    health_score: float = 0.0
    bot_phase: str = "parado"
    open_positions: int = 0
