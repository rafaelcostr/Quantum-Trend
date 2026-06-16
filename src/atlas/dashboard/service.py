from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

from atlas.brokers.binance import BinanceDemoBroker, BinanceLiveBroker, credentials_configured, fetch_public_candles
from atlas.core.config import AtlasConfig
from atlas.core.indicators import add_indicators, row_to_indicator_snapshot
from atlas.core.models import Candle, IndicatorSnapshot, Position, TradingMode
from atlas.strategies.registry import build_strategy_from_config


@dataclass
class LiveState:
    signal: str
    reason: str
    last_close: float
    last_time: datetime
    mm200: float | None
    mm20: float | None
    rsi: float | None
    adx: float | None
    usdt_free: float
    usdt_total: float
    btc_free: float
    btc_total: float
    equity_usdt: float
    in_position: bool
    updated_at: datetime
    balance_error: str | None = None


class DashboardService:
    """Read-only market + account snapshot for the live dashboard."""

    def __init__(self, config: AtlasConfig) -> None:
        self.config = config
        params = config.strategy.params
        self.strategy = build_strategy_from_config(config.strategy.name, params)
        self.warmup = int(params.get("warmup_bars", 205))
        self.params = params

        if config.mode == TradingMode.LIVE:
            self.broker = BinanceLiveBroker(config.exchange.symbol)
        else:
            self.broker = BinanceDemoBroker(config.exchange.symbol)

    def fetch_candles_df(self, limit: int = 350) -> pd.DataFrame:
        try:
            candles = self.broker.fetch_candles(
                self.config.exchange.symbol,
                self.config.exchange.timeframe,
                limit=limit,
            )
        except Exception:
            candles = fetch_public_candles(
                self.config.exchange.symbol,
                self.config.exchange.timeframe,
                limit=limit,
            )
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
        return add_indicators(
            df,
            bb_period=int(self.params.get("bb_period", 20)),
            bb_std=float(self.params.get("bb_std", 2.0)),
            rsi_period=int(self.params.get("rsi_period", 14)),
            adx_period=int(self.params.get("adx_period", 14)),
            sr_lookback=int(self.params.get("sr_lookback", 100)),
            sr_touch_pct=float(self.params.get("sr_touch_pct", 0.01)),
            mm_periods=[
                int(self.params.get("mm20_period", 20)),
                int(self.params.get("mm200_period", 200)),
            ],
            include_daily_macro=bool(self.params.get("include_daily_macro", False)),
            daily_mm_period=int(self.params.get("daily_mm_period", 200)),
        )

    def _snapshot(self, ind_df: pd.DataFrame, idx: int, closes: pd.Series) -> IndicatorSnapshot:
        snap = row_to_indicator_snapshot(ind_df.iloc[idx])
        if idx > 0:
            prev = row_to_indicator_snapshot(ind_df.iloc[idx - 1])
            snap["prev_bb_width"] = prev.get("bb_width")
            snap["prev_close"] = float(closes.iloc[idx - 1])
        return IndicatorSnapshot(timestamp=ind_df.index[idx].to_pydatetime(), **snap)

    def get_live_state(self, position: Position | None = None) -> LiveState:
        ind_df = self.fetch_candles_df()
        idx = len(ind_df) - 2
        candle = Candle(
            timestamp=ind_df.index[idx].to_pydatetime(),
            open=float(ind_df.iloc[idx]["open"]),
            high=float(ind_df.iloc[idx]["high"]),
            low=float(ind_df.iloc[idx]["low"]),
            close=float(ind_df.iloc[idx]["close"]),
            volume=float(ind_df.iloc[idx]["volume"]),
        )
        indicators = self._snapshot(ind_df, idx, ind_df["close"])
        signal = self.strategy.evaluate(candle, indicators, position)

        balances = {
            "usdt_free": 0.0,
            "usdt_total": 0.0,
            "btc_free": 0.0,
            "btc_total": 0.0,
        }
        balance_error: str | None = None
        live = self.config.mode == TradingMode.LIVE
        if credentials_configured(live=live):
            try:
                balances = self.broker.get_account_balances()
            except Exception as exc:
                balance_error = str(exc)
        else:
            balance_error = (
                "Chaves API ausentes no .env — grafico OK, saldo indisponivel. "
                "Va em Paper Trading > Validar API."
            )

        mark = candle.close
        equity = balances["usdt_total"] + balances["btc_total"] * mark

        return LiveState(
            signal=signal.action.value,
            reason=signal.reason,
            last_close=mark,
            last_time=candle.timestamp,
            mm200=indicators.mm200,
            mm20=indicators.mm20,
            rsi=indicators.rsi,
            adx=indicators.adx,
            usdt_free=balances["usdt_free"],
            usdt_total=balances["usdt_total"],
            btc_free=balances["btc_free"],
            btc_total=balances["btc_total"],
            equity_usdt=equity,
            in_position=balances["btc_total"] > 0.0001,
            updated_at=datetime.now(timezone.utc),
            balance_error=balance_error,
        )


def load_journal_events(
    database_url: str,
    mode: str,
    limit: int = 40,
    fallback_dir: Path | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT ts, event, symbol, payload
                    FROM journal
                    WHERE mode = :mode
                    ORDER BY ts DESC
                    LIMIT :limit
                    """
                ),
                {"mode": mode, "limit": limit},
            )
            for row in result:
                rows.append(
                    {
                        "ts": row.ts,
                        "event": row.event,
                        "symbol": row.symbol,
                        "payload": row.payload,
                    }
                )
        return rows
    except Exception:
        pass

    path = (fallback_dir or Path("data/journal")) / f"{mode}.jsonl"
    if not path.is_file():
        return []

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    for line in reversed(lines[-limit:]):
        try:
            item = json.loads(line)
            rows.append(
                {
                    "ts": item.get("ts"),
                    "event": item.get("event"),
                    "symbol": item.get("symbol"),
                    "payload": item.get("payload", {}),
                }
            )
        except json.JSONDecodeError:
            continue
    return rows
