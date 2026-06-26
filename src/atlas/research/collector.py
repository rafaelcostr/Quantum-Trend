"""Coleta OHLCV Binance com cache CSV local."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from atlas.brokers.binance import fetch_ohlcv_history
from atlas.core.config import AtlasConfig
from atlas.core.log import logger

# BTC/USDT spot na Binance (~ago/2017). Usado para detectar cache truncado.
_BTC_USDT_FULL_START = pd.Timestamp("2017-08-17", tz="UTC")


def cache_path(config: AtlasConfig) -> Path:
    sym = config.exchange.symbol.replace("/", "")
    return Path(config.data.cache_dir) / f"{config.exchange.id}_{sym}_{config.exchange.timeframe}.csv"


def _cache_needs_refresh(df: pd.DataFrame, config: AtlasConfig) -> bool:
    if df.empty:
        return True
    if len(df) <= 1001:
        return True

    years = config.data.years
    tf = config.exchange.timeframe.lower()
    span_days = (df.index.max() - df.index.min()).days

    if years <= 0:
        if "BTC" in config.exchange.symbol.upper() and tf == "1d":
            if df.index.min() > _BTC_USDT_FULL_START + pd.Timedelta(days=120):
                return True
            if span_days < 2500:
                return True
        if tf == "4h" and span_days < 2500:
            return True
        if tf == "1h" and span_days < 365:
            return True
        return False

    min_start = pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=years)
    if df.index.min() > min_start + pd.Timedelta(days=45):
        return True
    return False


def load_or_download(config: AtlasConfig, force: bool = False) -> pd.DataFrame:
    cache = cache_path(config)
    if cache.exists() and not force:
        df = pd.read_csv(cache, parse_dates=["timestamp"], index_col="timestamp")
        if not df.empty:
            df.index = pd.to_datetime(df.index, utc=True)
            if not _cache_needs_refresh(df, config):
                return df
            logger.info(
                "Cache %s incompleto (%s candles) — baixando histórico completo",
                cache.name,
                len(df),
            )

    years = config.data.years
    logger.info(
        "Baixando OHLCV %s %s (years=%s = %s)",
        config.exchange.symbol,
        config.exchange.timeframe,
        years,
        "histórico completo" if years <= 0 else f"últimos {years} anos",
    )
    df = fetch_ohlcv_history(
        config.exchange.symbol,
        config.exchange.timeframe,
        years=years,
    )
    if df.empty:
        raise RuntimeError(
            f"Nenhum candle baixado para {config.exchange.symbol} {config.exchange.timeframe}"
        )
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df.index = pd.to_datetime(df.index, utc=True)
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.reset_index().to_csv(cache, index=False)
    logger.info(
        "Cache salvo: %s (%s candles, %s -> %s)",
        cache.name,
        len(df),
        df.index.min().date(),
        df.index.max().date(),
    )
    return df
