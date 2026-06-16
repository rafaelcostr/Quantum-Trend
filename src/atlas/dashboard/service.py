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
from atlas.core.models import Candle, IndicatorSnapshot, Position, Side, TradingMode
from atlas.research.collector import cache_path, load_or_download, load_parquet
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
    quote_asset: str = "USDT"
    quote_free: float = 0.0
    quote_total: float = 0.0


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

    def _add_indicators(self, raw: pd.DataFrame) -> pd.DataFrame:
        return add_indicators(
            raw,
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

    def _load_raw_ohlcv(self, need_bars: int) -> pd.DataFrame:
        """Prefer local Parquet cache (instant); fallback to public API."""
        cache = cache_path(self.config)
        if cache.is_file():
            try:
                raw = load_parquet(cache)
                if not raw.empty:
                    return raw.tail(need_bars)
            except Exception:
                pass

        try:
            df = load_or_download(self.config, force=False)
            if not df.empty:
                return df.tail(need_bars)
        except Exception:
            pass

        candles = fetch_public_candles(
            self.config.exchange.symbol,
            self.config.exchange.timeframe,
            limit=min(need_bars, 500),
        )
        if not candles:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        return pd.DataFrame(
            {
                "open": [c.open for c in candles],
                "high": [c.high for c in candles],
                "low": [c.low for c in candles],
                "close": [c.close for c in candles],
                "volume": [c.volume for c in candles],
            },
            index=pd.DatetimeIndex([c.timestamp for c in candles]),
        )

    def fetch_candles_df(self, limit: int = 350) -> pd.DataFrame:
        need = limit + self.warmup + 10
        raw = self._load_raw_ohlcv(need)
        if raw.empty:
            return raw
        return self._add_indicators(raw).tail(limit)

    def fetch_chart_bootstrap_df(self, bars: int = 120) -> pd.DataFrame:
        """OHLCV rapido para o grafico ao vivo (MM recalculado no browser)."""
        need = bars + self.warmup + 10
        raw = self._load_raw_ohlcv(min(need, 500))
        if raw.empty:
            return raw
        return self._add_indicators(raw).tail(bars)

    def fetch_demo_balances(self) -> tuple[dict[str, float] | None, str | None]:
        """Saldo demo/live automatico quando as chaves existem no .env."""
        live = self.config.mode == TradingMode.LIVE
        if not credentials_configured(live=live):
            return None, (
                "Chaves API ausentes no .env — preencha BINANCE_DEMO_API_KEY e "
                "BINANCE_DEMO_API_SECRET (demo.binance.com)."
            )
        try:
            quote = self.config.exchange.symbol.split("/")[-1].upper()
            return self.broker.get_account_balances(quote_asset=quote), None
        except Exception as exc:
            return None, str(exc)

    def fetch_demo_trades(self, *, limit: int = 500) -> tuple[list[dict], str | None]:
        live = self.config.mode == TradingMode.LIVE
        if not credentials_configured(live=live):
            return [], "Chaves API ausentes no .env"
        try:
            return self.broker.fetch_my_trades(limit=limit), None
        except Exception as exc:
            return [], str(exc)

    def _snapshot(self, ind_df: pd.DataFrame, idx: int, closes: pd.Series) -> IndicatorSnapshot:
        snap = row_to_indicator_snapshot(ind_df.iloc[idx])
        if idx > 0:
            prev = row_to_indicator_snapshot(ind_df.iloc[idx - 1])
            snap["prev_bb_width"] = prev.get("bb_width")
            snap["prev_close"] = float(closes.iloc[idx - 1])
        return IndicatorSnapshot(timestamp=ind_df.index[idx].to_pydatetime(), **snap)

    def _position_from_balances(self, balances: dict[str, float]) -> Position | None:
        qty = balances.get("btc_total", 0.0)
        if qty <= 0.0001:
            return None
        return Position(
            symbol=self.config.exchange.symbol,
            side=Side.BUY,
            quantity=qty,
            entry_price=0.0,
            entry_time=datetime.now(timezone.utc),
            metadata={"source": "exchange_balance"},
        )

    def get_live_state(
        self,
        position: Position | None = None,
        *,
        ind_df: pd.DataFrame | None = None,
        balances: dict[str, float] | None = None,
        balance_error: str | None = None,
    ) -> LiveState:
        if ind_df is None:
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

        if balances is None and balance_error is None:
            balances, balance_error = self.fetch_demo_balances()

        if balances is None:
            quote = self.config.exchange.symbol.split("/")[-1].upper()
            balances = {
                "quote_asset": quote,
                "quote_free": 0.0,
                "quote_total": 0.0,
                "usdt_free": 0.0,
                "usdt_total": 0.0,
                "btc_free": 0.0,
                "btc_total": 0.0,
            }

        if position is None:
            position = self._position_from_balances(balances)

        signal = self.strategy.evaluate(candle, indicators, position)

        mark = candle.close
        quote_asset = str(balances.get("quote_asset") or self.config.exchange.symbol.split("/")[-1]).upper()
        quote_total = float(balances.get("quote_total") or balances.get("usdt_total", 0))
        quote_free = float(balances.get("quote_free") or balances.get("usdt_free", 0))
        equity = quote_total + balances["btc_total"] * mark

        return LiveState(
            signal=signal.action.value,
            reason=signal.reason,
            last_close=mark,
            last_time=candle.timestamp,
            mm200=indicators.mm200,
            mm20=indicators.mm20,
            rsi=indicators.rsi,
            adx=indicators.adx,
            usdt_free=float(balances.get("usdt_free", quote_free if quote_asset == "USDT" else 0)),
            usdt_total=float(balances.get("usdt_total", quote_total if quote_asset == "USDT" else 0)),
            btc_free=balances["btc_free"],
            btc_total=balances["btc_total"],
            equity_usdt=equity,
            in_position=balances["btc_total"] > 0.0001,
            updated_at=datetime.now(timezone.utc),
            balance_error=balance_error,
            quote_asset=quote_asset,
            quote_free=quote_free,
            quote_total=quote_total,
        )


def fetch_demo_balances(config: AtlasConfig) -> tuple[dict[str, float] | None, str | None]:
    """Helper de modulo para o dashboard."""
    return DashboardService(config).fetch_demo_balances()


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
