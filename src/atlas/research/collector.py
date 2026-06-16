from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ccxt
import pandas as pd
from sqlalchemy import create_engine, text

from atlas.core.config import AtlasConfig
from atlas.core.models import Candle


TIMEFRAME_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def create_exchange(exchange_id: str) -> ccxt.Exchange:
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True})


def fetch_ohlcv_history(
    exchange: ccxt.Exchange,
    symbol: str,
    timeframe: str,
    years: int = 3,
) -> pd.DataFrame:
    if timeframe not in TIMEFRAME_MS:
        raise ValueError(f"unsupported timeframe: {timeframe}")

    since_dt = datetime.now(timezone.utc) - timedelta(days=365 * years)
    since_ms = int(since_dt.timestamp() * 1000)
    all_rows: list[list] = []

    while True:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=1000)
        if not batch:
            break
        all_rows.extend(batch)
        since_ms = batch[-1][0] + TIMEFRAME_MS[timeframe]
        if since_ms >= int(datetime.now(timezone.utc).timestamp() * 1000):
            break
        time.sleep(exchange.rateLimit / 1000 if exchange.rateLimit else 0.2)

    if not all_rows:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
    df = df.set_index("timestamp")
    return df


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def load_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def cache_path(config: AtlasConfig) -> Path:
    sym = config.exchange.symbol.replace("/", "")
    return Path(config.data.cache_dir) / f"{config.exchange.id}_{sym}_{config.exchange.timeframe}.parquet"


def download_and_cache(config: AtlasConfig) -> pd.DataFrame:
    cache = cache_path(config)
    exchange = create_exchange(config.exchange.id)
    df = fetch_ohlcv_history(
        exchange,
        config.exchange.symbol,
        config.exchange.timeframe,
        years=config.data.years,
    )
    save_parquet(df, cache)
    return df


def load_or_download(config: AtlasConfig, force: bool = False) -> pd.DataFrame:
    cache = cache_path(config)
    if cache.exists() and not force:
        return load_parquet(cache)
    return download_and_cache(config)


def save_candles_to_db(config: AtlasConfig, df: pd.DataFrame) -> int:
    engine = create_engine(config.database_url)
    records = []
    for ts, row in df.iterrows():
        records.append(
            {
                "exchange": config.exchange.id,
                "symbol": config.exchange.symbol,
                "timeframe": config.exchange.timeframe,
                "ts": ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            }
        )

    if not records:
        return 0

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO candles (exchange, symbol, timeframe, ts, open, high, low, close, volume)
                VALUES (:exchange, :symbol, :timeframe, :ts, :open, :high, :low, :close, :volume)
                ON CONFLICT (exchange, symbol, timeframe, ts) DO NOTHING
                """
            ),
            records,
        )
    return len(records)


def load_candles_from_db(config: AtlasConfig) -> pd.DataFrame:
    engine = create_engine(config.database_url)
    query = text(
        """
        SELECT ts, open, high, low, close, volume
        FROM candles
        WHERE exchange = :exchange AND symbol = :symbol AND timeframe = :timeframe
        ORDER BY ts
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(
            query,
            conn,
            params={
                "exchange": config.exchange.id,
                "symbol": config.exchange.symbol,
                "timeframe": config.exchange.timeframe,
            },
            parse_dates=["ts"],
            index_col="ts",
        )
    if not df.empty:
        df.index = pd.to_datetime(df.index, utc=True)
    return df
