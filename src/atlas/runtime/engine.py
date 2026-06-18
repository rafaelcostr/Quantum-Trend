from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from atlas.brokers.binance import BinanceDemoBroker, BinanceLiveBroker
from atlas.core.config import AtlasConfig
from atlas.core.indicators import add_indicators_from_params, row_to_indicator_snapshot
from atlas.core.models import (
    Candle,
    IndicatorSnapshot,
    Order,
    PortfolioState,
    Position,
    Side,
    SignalAction,
    TradingMode,
)
from atlas.core.risk import RiskManager
from atlas.monitoring.alerts import TelegramAlerts
from atlas.monitoring.watchdog import AlertWatchdog
from atlas.quantum.journal_enricher import build_trade_journal_payload
from atlas.quantum.multi_timeframe import build_execution_dataset
from atlas.quantum.runtime_store import update_runtime_snapshot
from atlas.runtime.journal import Journal
from atlas.runtime.reconciler import PositionReconciler
from atlas.runtime.risk_store import is_trading_paused, record_trade_close, record_trade_open
from atlas.strategies.registry import build_strategy_from_config


class TradingEngine:
    """Loop paper/live compartilhado — reconciliação, risco e watchdog."""

    def __init__(self, config: AtlasConfig) -> None:
        self.config = config
        if config.mode in (TradingMode.PAPER, TradingMode.LIVE):
            self._require_api_credentials(config.mode)

        params = config.strategy.params
        self.strategy = build_strategy_from_config(config.strategy.name, params)
        self.multi_timeframe = getattr(self.strategy, "uses_multi_timeframe", False)
        self.risk = RiskManager(config.risk)
        if os.getenv("ATLAS_KILL_SWITCH", "0").strip() in {"1", "true", "yes"}:
            self.risk.activate_kill_switch("env")
        self.journal = Journal(config.database_url, config.mode)
        self.alerts = TelegramAlerts()
        self.watchdog = AlertWatchdog(
            self.alerts,
            alert_on_signal=config.runtime.alert_on_signal,
            drawdown_alert_pct=config.runtime.drawdown_alert_pct,
        )
        self.warmup = int(params.get("warmup_bars", 250 if self.multi_timeframe else 205))

        if config.mode == TradingMode.LIVE:
            self.broker = BinanceLiveBroker(config.exchange.symbol)
        else:
            self.broker = BinanceDemoBroker(config.exchange.symbol)

        self._reconciler = PositionReconciler(
            journal=self.journal,
            broker=self.broker,
            symbol=config.exchange.symbol,
        )
        from atlas.platform.orchestrator import platform_orchestrator

        self._position, self._reconcile_meta = platform_orchestrator.startup_recovery(
            self._reconciler,
            symbol=config.exchange.symbol,
            strategy=config.strategy.name,
        )
        self._last_reconcile = time.monotonic()
        self.last_tick_at: datetime | None = None
        self.last_error: str | None = None
        self.ticks = 0
        self._last_context = None

    @staticmethod
    def _require_api_credentials(mode: TradingMode) -> None:
        if mode == TradingMode.PAPER:
            key = os.getenv("BINANCE_DEMO_API_KEY", "").strip()
            secret = os.getenv("BINANCE_DEMO_API_SECRET", "").strip()
            label = "BINANCE_DEMO_API_KEY / BINANCE_DEMO_API_SECRET"
        else:
            key = os.getenv("BINANCE_LIVE_API_KEY", "").strip()
            secret = os.getenv("BINANCE_LIVE_API_SECRET", "").strip()
            label = "BINANCE_LIVE_API_KEY / BINANCE_LIVE_API_SECRET"
        if key and secret:
            return
        env_hint = (
            "Copie .env.example para .env e preencha as chaves."
            if not (Path.cwd() / ".env").is_file()
            else f"Chaves vazias — configure {label}."
        )
        raise RuntimeError(f"API keys missing for {mode.value} mode. {env_hint}")

    def _build_indicators(self, candles: list[Candle]) -> pd.DataFrame:
        df = pd.DataFrame(
            {
                "open": [c.open for c in candles],
                "high": [c.high for c in candles],
                "low": [c.low for c in candles],
                "close": [c.close for c in candles],
                "volume": [c.volume for c in candles],
            },
            index=pd.DatetimeIndex([c.timestamp for c in candles]),
        )
        return add_indicators_from_params(df, self.config.strategy.params)

    def _execution_dataframe(self) -> pd.DataFrame:
        if self.multi_timeframe:
            return build_execution_dataset(self.config)
        candles = self.broker.fetch_candles(
            self.config.exchange.symbol,
            self.config.exchange.timeframe,
            limit=500,
        )
        return self._build_indicators(candles)

    def _snapshot(self, ind_df: pd.DataFrame, idx: int, candles: list[Candle]) -> IndicatorSnapshot:
        snap = row_to_indicator_snapshot(ind_df.iloc[idx])
        if idx > 0:
            prev = row_to_indicator_snapshot(ind_df.iloc[idx - 1])
            snap["prev_bb_width"] = prev.get("bb_width")
            snap["prev_close"] = float(candles[idx - 1].close)
        return IndicatorSnapshot(timestamp=candles[idx].timestamp, **snap)

    def _evaluate_signal(self, ind_df: pd.DataFrame, idx: int, candle: Candle, position: Position | None):
        row = ind_df.iloc[idx]
        if self.multi_timeframe and hasattr(self.strategy, "evaluate_context"):
            ctx = self.strategy.build_context(row, candle)
            self._last_context = ctx
            signal = self.strategy.evaluate_context(ctx, position)
            update_runtime_snapshot(
                alignment_score=ctx.alignment_score,
                alignment_breakdown=ctx.alignment_breakdown,
                regime=ctx.regime.value,
                regime_label=ctx.meta.get("regime_label"),
                bot_phase="operando" if position else "demo",
                last_signal=signal.action.value,
                last_reason=signal.reason,
                strategy=self.strategy.name,
            )
            return signal, ctx
        indicators = self._snapshot(ind_df, idx, [candle])
        return self.strategy.evaluate(candle, indicators, position), None

    def _log_trade(self, event: str, signal, candle: Candle, *, ctx=None, fill=None, position=None) -> None:
        payload = build_trade_journal_payload(
            event=event,
            signal=signal,
            candle=candle,
            ctx=ctx,
            position=position,
        )
        if fill is not None:
            payload["fill"] = fill
        self.journal.log(event, self.config.exchange.symbol, **payload)

    def process_once(self) -> dict:
        from atlas.platform.orchestrator import platform_orchestrator

        self.ticks += 1
        self.last_tick_at = datetime.now(timezone.utc)
        ind_df = self._execution_dataframe()
        if len(ind_df) < self.warmup + 2:
            update_runtime_snapshot(bot_phase="analisando", strategy=self.strategy.name)
            return {"status": "warming_up", "candles": len(ind_df)}

        dq = platform_orchestrator.assess_tick_data(self, ind_df)
        can_trade, gate_reason = platform_orchestrator.gate_operations(self, data_ok=dq.get("ok", True))

        idx = len(ind_df) - 2
        row = ind_df.iloc[idx]
        ts = ind_df.index[idx]
        candle = Candle(
            timestamp=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row.get("volume", 0)),
        )
        position = self._position
        signal, ctx = self._evaluate_signal(ind_df, idx, candle, position)
        result = {"status": "ok", "signal": signal.action.value, "reason": signal.reason}

        try:
            cash = self.broker.get_balance()
        except Exception as exc:
            cash = self.config.risk.initial_capital
            result["balance_warning"] = str(exc)

        mark = candle.close
        equity = cash + (position.quantity * mark if position else 0)
        portfolio = PortfolioState(cash=cash, equity=equity, position=position)
        result["equity"] = equity

        if signal.action == SignalAction.EXIT_LONG and position:
            if not can_trade:
                result["action"] = "blocked"
                result["block_reason"] = gate_reason
                platform_orchestrator.post_signal(self, signal=signal, ctx=ctx, outcome=result, candle=candle)
                return result
            decision = self.risk.approve_exit(signal, portfolio)
            if decision.approved:
                order = Order(symbol=self.config.exchange.symbol, side=Side.SELL, quantity=position.quantity)
                fill = self.broker.place_order(order)
                pnl = (fill.filled_price or mark - position.entry_price) * position.quantity if fill.success else 0
                self._log_trade("exit", signal, candle, ctx=ctx, fill=fill.model_dump(), position=position)
                if fill.success:
                    record_trade_close(pnl=pnl)
                self.alerts.trade_exit(
                    self.config.exchange.symbol,
                    position.entry_price,
                    fill.filled_price or mark,
                    position.quantity,
                    signal.reason,
                    self.config.mode.value,
                )
                self._position = None
                result["action"] = "exit"
            alert_meta = self.watchdog.process(
                symbol=self.config.exchange.symbol,
                mode=self.config.mode.value,
                signal=signal.action.value,
                reason=signal.reason,
                equity=equity,
                trade_executed=result.get("action") == "exit",
            )
            result.update(alert_meta)
            platform_orchestrator.post_signal(self, signal=signal, ctx=ctx, outcome=result, candle=candle)
            return result
            if not can_trade:
                result["action"] = "blocked"
                result["block_reason"] = gate_reason
                platform_orchestrator.post_signal(self, signal=signal, ctx=ctx, outcome=result, candle=candle)
                return result
            ok_filter, filter_reason = platform_orchestrator.check_entry_filters(self, ind_df, idx)
            if not ok_filter:
                result["action"] = "blocked"
                result["block_reason"] = filter_reason
                platform_orchestrator.post_signal(self, signal=signal, ctx=ctx, outcome=result, candle=candle)
                return result
            paused, pause_reason = is_trading_paused()
            if paused:
                result["action"] = "paused"
                result["block_reason"] = pause_reason
                return result
            if "balance_warning" in result:
                result["action"] = "skipped_no_balance"
                return result
            decision = self.risk.approve_entry(signal, portfolio, candle.timestamp, candle.close)
            if decision.approved:
                order = Order(
                    symbol=self.config.exchange.symbol,
                    side=Side.BUY,
                    quantity=decision.quantity,
                    stop_price=signal.stop_price,
                )
                fill = self.broker.place_order(order)
                if fill.success:
                    self._position = Position(
                        symbol=self.config.exchange.symbol,
                        side=Side.BUY,
                        quantity=fill.filled_quantity or decision.quantity,
                        entry_price=fill.filled_price or candle.close,
                        entry_time=datetime.now(timezone.utc),
                        stop_price=signal.stop_price,
                        target_price=signal.target_price,
                        metadata=signal.metadata,
                    )
                    self._log_trade("entry", signal, candle, ctx=ctx, fill=fill.model_dump())
                    record_trade_open()
                    self.alerts.trade_entry(
                        self.config.exchange.symbol,
                        fill.filled_price or candle.close,
                        fill.filled_quantity or decision.quantity,
                        signal.reason,
                        self.config.mode.value,
                    )
                    result["action"] = "entry"
                else:
                    result["action"] = "entry_failed"
                    result["error"] = fill.message
            else:
                result["action"] = "blocked"
                result["block_reason"] = decision.reason

        alert_meta = self.watchdog.process(
            symbol=self.config.exchange.symbol,
            mode=self.config.mode.value,
            signal=signal.action.value,
            reason=signal.reason,
            equity=equity,
            trade_executed=result.get("action") in {"entry", "exit"},
        )
        result.update(alert_meta)
        platform_orchestrator.post_signal(self, signal=signal, ctx=ctx, outcome=result, candle=candle)
        return result

    def run_forever(self) -> None:
        self.journal.log(
            "runner_start",
            self.config.exchange.symbol,
            strategy=self.strategy.name,
            reconcile=self._reconcile_meta,
            multi_timeframe=self.multi_timeframe,
        )
        try:
            self.watchdog.reset_peak(self.broker.get_balance())
        except Exception:
            self.watchdog.reset_peak(self.config.risk.initial_capital)
        poll = self.config.runtime.poll_seconds
        reconcile_secs = self.config.runtime.reconcile_minutes * 60
        while True:
            try:
                if time.monotonic() - self._last_reconcile >= reconcile_secs:
                    self._position, periodic_meta = self._reconciler.reconcile_periodic(self._position)
                    self._last_reconcile = time.monotonic()
                    if periodic_meta.get("action") not in (None, "ok"):
                        self.journal.log("reconcile", self.config.exchange.symbol, **periodic_meta)
                outcome = self.process_once()
                self.journal.log("tick", self.config.exchange.symbol, **outcome)
            except Exception as exc:
                self.last_error = str(exc)
                self.journal.log("error", self.config.exchange.symbol, error=str(exc))
                self.alerts.error(self.config.exchange.symbol, str(exc), self.config.mode.value)
            time.sleep(poll)
