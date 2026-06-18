"""Backtest event-driven completo — paridade com TradingEngine."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from atlas.brokers.simulated import SimulatedBroker
from atlas.core.config import AtlasConfig
from atlas.core.indicators import add_indicators_from_params, row_to_indicator_snapshot
from atlas.core.models import (
    Candle,
    IndicatorSnapshot,
    Order,
    PortfolioState,
    Side,
    SignalAction,
    Trade,
    TradingMode,
)
from atlas.core.risk import RiskManager
from atlas.strategies.registry import build_strategy_from_config


@dataclass
class BacktestResult:
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[tuple] = field(default_factory=list)
    initial_capital: float = 0.0
    final_equity: float = 0.0
    config: AtlasConfig | None = None


def _df_to_candles(df: pd.DataFrame) -> list[Candle]:
    candles = []
    for ts, row in df.iterrows():
        candles.append(
            Candle(
                timestamp=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
        )
    return candles


class Backtester:
    def __init__(self, config: AtlasConfig, df: pd.DataFrame) -> None:
        self.config = config
        params = config.strategy.params
        self.strategy = build_strategy_from_config(config.strategy.name, params)
        self.risk = RiskManager(config.risk)
        self.broker = SimulatedBroker(
            symbol=config.exchange.symbol,
            execution=config.execution,
            cash=config.risk.initial_capital,
        )
        self.multi_timeframe = getattr(self.strategy, "uses_multi_timeframe", False)
        if self.multi_timeframe:
            self.ind_df = df
            self.warmup = int(params.get("warmup_bars", 250))
        else:
            ind_df = add_indicators_from_params(df, params)
            self.ind_df = ind_df
            self.warmup = int(params.get("warmup_bars", max(200, int(params.get("mm200_period", 200)) + 5)))
        self.candles = _df_to_candles(self.ind_df)
        self.broker.set_candles(self.candles)

    def run(self) -> BacktestResult:
        trades: list[Trade] = []
        equity_curve: list[tuple] = []
        pending_signal = None

        for i in range(self.warmup, len(self.candles)):
            candle = self.candles[i]
            self.broker._cursor = i + 1  # noqa: SLF001

            if self.config.execution.entry_on_next_open and self.broker._pending_entry:  # noqa: SLF001
                fill = self.broker.execute_pending_at_open(candle)
                if fill and fill.success and self.broker.position:
                    pending_meta = pending_signal or {}
                    trades.append(
                        Trade(
                            symbol=self.config.exchange.symbol,
                            side=Side.BUY,
                            entry_time=candle.timestamp,
                            entry_price=fill.filled_price or candle.open,
                            quantity=fill.filled_quantity or 0,
                            stop_price=self.broker.position.stop_price,
                            target_price=self.broker.position.target_price,
                            fees=fill.fee,
                            strategy=self.strategy.name,
                            metadata={"reason": pending_meta.get("reason", ""), **(pending_meta.get("metadata") or {})},
                        )
                    )
                    pending_signal = None

            row = self.ind_df.iloc[i]
            snap = row_to_indicator_snapshot(row)
            if i > 0:
                prev = row_to_indicator_snapshot(self.ind_df.iloc[i - 1])
                snap["prev_bb_width"] = prev.get("bb_width")
                snap["prev_close"] = float(self.candles[i - 1].close)
            extra = {"_quantum_row": row} if self.multi_timeframe else {}
            indicators = IndicatorSnapshot(timestamp=candle.timestamp, extra=extra, **snap)
            open_trade = trades[-1] if trades and not trades[-1].is_closed else None
            position = self.broker.get_position(self.config.exchange.symbol)
            if position and open_trade and open_trade.metadata:
                position = position.model_copy(update={"metadata": open_trade.metadata})
            if self.multi_timeframe and hasattr(self.strategy, "evaluate_context"):
                ctx = self.strategy.build_context(row, candle)
                signal = self.strategy.evaluate_context(ctx, position)
            else:
                signal = self.strategy.evaluate(candle, indicators, position)

            if open_trade and signal.action == SignalAction.EXIT_LONG:
                exit_price = candle.close
                if position and position.stop_price and candle.low <= position.stop_price:
                    exit_price = position.stop_price
                elif position and position.target_price and candle.high >= position.target_price:
                    exit_price = position.target_price
                order = Order(symbol=self.config.exchange.symbol, side=Side.SELL, quantity=open_trade.quantity)
                result = self.broker.place_order(order)
                if result.success:
                    open_trade.exit_time = candle.timestamp
                    open_trade.exit_price = result.filled_price or exit_price
                    open_trade.fees += result.fee
                    gross = (open_trade.exit_price - open_trade.entry_price) * open_trade.quantity
                    open_trade.pnl = gross - open_trade.fees
                    if open_trade.entry_price > 0:
                        open_trade.pnl_pct = open_trade.pnl / (open_trade.entry_price * open_trade.quantity)

            elif (
                signal.action == SignalAction.ENTER_LONG
                and open_trade is None
                and not self.broker._pending_entry  # noqa: SLF001
            ):
                portfolio = PortfolioState(
                    cash=self.broker.cash,
                    equity=self.broker.equity(candle.close),
                    position=position,
                )
                decision = self.risk.approve_entry(signal, portfolio, candle.timestamp, candle.close)
                if decision.approved:
                    pending_signal = {"reason": signal.reason, "metadata": signal.metadata}
                    if self.config.execution.entry_on_next_open:
                        self.broker.queue_entry_next_open(
                            decision.quantity, signal.stop_price, signal.target_price, metadata=signal.metadata
                        )
                    else:
                        order = Order(
                            symbol=self.config.exchange.symbol,
                            side=Side.BUY,
                            quantity=decision.quantity,
                            stop_price=signal.stop_price,
                        )
                        result = self.broker.place_order(order)
                        if result.success and self.broker.position:
                            trades.append(
                                Trade(
                                    symbol=self.config.exchange.symbol,
                                    side=Side.BUY,
                                    entry_time=candle.timestamp,
                                    entry_price=result.filled_price or candle.close,
                                    quantity=result.filled_quantity or decision.quantity,
                                    stop_price=signal.stop_price,
                                    target_price=signal.target_price,
                                    fees=result.fee,
                                    strategy=self.strategy.name,
                                    metadata={"reason": signal.reason, **signal.metadata},
                                )
                            )

            equity_curve.append((candle.timestamp, self.broker.equity(candle.close)))

        final = equity_curve[-1][1] if equity_curve else self.config.risk.initial_capital
        return BacktestResult(
            trades=[t for t in trades if t.is_closed],
            equity_curve=equity_curve,
            initial_capital=self.config.risk.initial_capital,
            final_equity=final,
            config=self.config,
        )


def run_backtest_engine(config: AtlasConfig, df: pd.DataFrame) -> BacktestResult:
    config.mode = TradingMode.BACKTEST
    return Backtester(config, df).run()
