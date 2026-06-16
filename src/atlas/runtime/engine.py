from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from atlas.brokers.binance import BinanceDemoBroker, BinanceLiveBroker
from atlas.core.config import AtlasConfig
from atlas.core.indicators import add_indicators, row_to_indicator_snapshot
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
from atlas.runtime.journal import Journal
from atlas.runtime.reconciler import PositionReconciler
from atlas.strategies.registry import build_strategy_from_config


class TradingEngine:
    """Shared live/paper evaluation loop."""

    def __init__(self, config: AtlasConfig) -> None:
        self.config = config
        if config.mode in (TradingMode.PAPER, TradingMode.LIVE):
            self._require_api_credentials(config.mode)

        params = config.strategy.params
        self.strategy = build_strategy_from_config(config.strategy.name, params)
        self.risk = RiskManager(config.risk)
        self.journal = Journal(config.database_url, config.mode)
        self.alerts = TelegramAlerts()
        self.watchdog = AlertWatchdog(
            self.alerts,
            alert_on_signal=config.runtime.alert_on_signal,
            drawdown_alert_pct=config.runtime.drawdown_alert_pct,
        )
        self.warmup = int(params.get("warmup_bars", 205))

        if config.mode == TradingMode.LIVE:
            self.broker = BinanceLiveBroker(config.exchange.symbol)
        else:
            self.broker = BinanceDemoBroker(config.exchange.symbol)

        self._reconciler = PositionReconciler(
            journal=self.journal,
            broker=self.broker,
            symbol=config.exchange.symbol,
        )
        self._position, self._reconcile_meta = self._reconciler.reconcile_on_startup()
        self._last_reconcile = time.monotonic()

    @staticmethod
    def _require_api_credentials(mode: TradingMode) -> None:
        if mode == TradingMode.PAPER:
            key = os.getenv("BINANCE_DEMO_API_KEY", "").strip()
            secret = os.getenv("BINANCE_DEMO_API_SECRET", "").strip()
            label = "BINANCE_DEMO_API_KEY / BINANCE_DEMO_API_SECRET"
            help_url = "https://demo.binance.com"
        else:
            key = os.getenv("BINANCE_LIVE_API_KEY", "").strip()
            secret = os.getenv("BINANCE_LIVE_API_SECRET", "").strip()
            label = "BINANCE_LIVE_API_KEY / BINANCE_LIVE_API_SECRET"
            help_url = "https://www.binance.com"

        if key and secret:
            return

        env_hint = (
            "Copy .env.example to .env and fill in your keys."
            if not (Path.cwd() / ".env").is_file()
            else f"Keys in .env are empty — set {label}."
        )
        raise RuntimeError(
            f"API keys missing for {mode.value} mode. {env_hint} "
            f"Demo keys: {help_url}"
        )

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
        params = self.config.strategy.params
        return add_indicators(
            df,
            bb_period=int(params.get("bb_period", 20)),
            bb_std=float(params.get("bb_std", 2.0)),
            rsi_period=int(params.get("rsi_period", 14)),
            adx_period=int(params.get("adx_period", 14)),
            sr_lookback=int(params.get("sr_lookback", 100)),
            sr_touch_pct=float(params.get("sr_touch_pct", 0.01)),
            mm_periods=[
                int(params.get("mm20_period", 20)),
                int(params.get("mm200_period", 200)),
            ],
            include_daily_macro=bool(params.get("include_daily_macro", False)),
            daily_mm_period=int(params.get("daily_mm_period", 200)),
        )

    def _snapshot(self, ind_df: pd.DataFrame, idx: int, candles: list[Candle]) -> IndicatorSnapshot:
        snap = row_to_indicator_snapshot(ind_df.iloc[idx])
        if idx > 0:
            prev = row_to_indicator_snapshot(ind_df.iloc[idx - 1])
            snap["prev_bb_width"] = prev.get("bb_width")
            snap["prev_close"] = float(candles[idx - 1].close)
        return IndicatorSnapshot(timestamp=candles[idx].timestamp, **snap)

    def process_once(self) -> dict:
        """Evaluate latest closed candle and optionally trade."""
        candles = self.broker.fetch_candles(
            self.config.exchange.symbol,
            self.config.exchange.timeframe,
            limit=500,
        )
        if len(candles) < self.warmup + 2:
            return {"status": "warming_up", "candles": len(candles)}

        ind_df = self._build_indicators(candles)
        idx = len(candles) - 2  # last fully closed candle
        candle = candles[idx]
        indicators = self._snapshot(ind_df, idx, candles)
        position = self._position

        signal = self.strategy.evaluate(candle, indicators, position)
        result = {"status": "ok", "signal": signal.action.value, "reason": signal.reason}

        try:
            cash = self.broker.get_balance()
        except Exception as exc:
            cash = self.config.risk.initial_capital
            result["balance_warning"] = (
                f"Saldo demo indisponível ({exc}). "
                "Usando capital simulado para avaliar sinal; ordens reais não serão enviadas."
            )
        mark = candle.close
        equity = cash + (position.quantity * mark if position else 0)
        portfolio = PortfolioState(cash=cash, equity=equity, position=position)
        result["equity"] = equity
        result["usdt_free"] = cash
        result["btc_qty"] = position.quantity if position else 0.0
        result["mark_price"] = mark

        trade_executed = False

        if signal.action == SignalAction.EXIT_LONG and position:
            order = Order(
                symbol=self.config.exchange.symbol,
                side=Side.SELL,
                quantity=position.quantity,
            )
            fill = self.broker.place_order(order)
            self.journal.log("exit", self.config.exchange.symbol, signal=signal.reason, fill=fill.model_dump())
            self.alerts.trade_exit(
                self.config.exchange.symbol,
                fill.filled_price or mark,
                position.quantity,
                signal.reason,
                self.config.mode.value,
            )
            self._position = None
            result["action"] = "exit"
            trade_executed = True
            alert_meta = self.watchdog.process(
                symbol=self.config.exchange.symbol,
                mode=self.config.mode.value,
                signal=signal.action.value,
                reason=signal.reason,
                equity=equity,
                trade_executed=True,
            )
            result.update(alert_meta)
            return result

        if signal.action == SignalAction.ENTER_LONG and position is None:
            if "balance_warning" in result:
                result["action"] = "skipped_no_balance"
                alert_meta = self.watchdog.process(
                    symbol=self.config.exchange.symbol,
                    mode=self.config.mode.value,
                    signal=signal.action.value,
                    reason=signal.reason,
                    equity=equity,
                    trade_executed=False,
                )
                result.update(alert_meta)
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
                    self.journal.log(
                        "entry",
                        self.config.exchange.symbol,
                        signal=signal.reason,
                        fill=fill.model_dump(),
                        metadata=signal.metadata,
                        stop_price=signal.stop_price,
                        target_price=signal.target_price,
                    )
                    self.alerts.trade_entry(
                        self.config.exchange.symbol,
                        fill.filled_price or candle.close,
                        fill.filled_quantity or decision.quantity,
                        signal.reason,
                        self.config.mode.value,
                    )
                    result["action"] = "entry"
                    trade_executed = True
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
            trade_executed=trade_executed,
        )
        result.update(alert_meta)
        return result

    def run_forever(self) -> None:
        self.journal.log(
            "runner_start",
            self.config.exchange.symbol,
            strategy=self.strategy.name,
            reconcile=self._reconcile_meta,
            restored_position=self._position.model_dump(mode="json") if self._position else None,
        )
        if self.alerts.enabled:
            pos_txt = (
                f"Posição restaurada: {self._position.quantity:.6f} BTC"
                if self._position
                else "Posição: flat"
            )
            self.alerts.send(
                f"🚀 ATLAS {self.config.mode.value.upper()} iniciado\n"
                f"Estratégia: {self.strategy.name}\n"
                f"Par: {self.config.exchange.symbol} {self.config.exchange.timeframe}\n"
                f"{pos_txt}\n"
                f"Alertas sinal: {'ON' if self.config.runtime.alert_on_signal else 'OFF'}\n"
                f"Alerta DD: {self.config.runtime.drawdown_alert_pct:.0%}"
            )
        try:
            cash = self.broker.get_balance()
            self.watchdog.reset_peak(cash)
        except Exception:
            self.watchdog.reset_peak(self.config.risk.initial_capital)
        poll = self.config.runtime.poll_seconds
        reconcile_secs = self.config.runtime.reconcile_minutes * 60
        while True:
            try:
                if time.monotonic() - self._last_reconcile >= reconcile_secs:
                    self._position, periodic_meta = self._reconciler.reconcile_periodic(self._position)
                    if periodic_meta.get("action") not in (None, "ok"):
                        self.journal.log(
                            "reconcile",
                            self.config.exchange.symbol,
                            **periodic_meta,
                            position=self._position.model_dump(mode="json") if self._position else None,
                        )
                    self._last_reconcile = time.monotonic()
                outcome = self.process_once()
                self.journal.log("tick", self.config.exchange.symbol, **outcome)
            except Exception as exc:
                self.journal.log("error", self.config.exchange.symbol, error=str(exc))
                self.alerts.error(self.config.exchange.symbol, str(exc), self.config.mode.value)
            time.sleep(poll)
