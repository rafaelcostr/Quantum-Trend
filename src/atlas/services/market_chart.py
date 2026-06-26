"""OHLCV + indicadores das estratégias para gráfico de mercados."""
from __future__ import annotations

import math
import time

import pandas as pd

from atlas.brokers.binance import fetch_public_candles
from atlas.core.external import classify_external_error
from atlas.core.indicators import add_indicators
from atlas.core.log import log_event
from atlas.core.symbols import build_symbol, validate_operated_base

_CHART_CACHE: dict[tuple[str, str], tuple[float, dict, str]] = {}
_CHART_TTL = 90.0
_WARMUP_BARS = 220
_DISPLAY_BARS = 240


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return round(v, 8)


def get_market_chart_payload(*, base: str = "BTC", quote: str = "USDT", timeframe: str = "4h") -> dict:
    base_u = validate_operated_base(base)
    tf = timeframe.lower()
    symbol = build_symbol(base_u, quote)
    key = (symbol, tf)
    now = time.time()
    cached = _CHART_CACHE.get(key)
    if cached and (now - cached[0]) < _CHART_TTL:
        return {**cached[1], "stale": False, "last_success_at": cached[2], "ttl_seconds": _CHART_TTL}

    limit = _WARMUP_BARS + _DISPLAY_BARS
    try:
        candles = fetch_public_candles(symbol, tf, limit=min(limit, 500))
    except Exception as exc:
        info = classify_external_error(exc)
        log_event(
            30,
            "market_chart.fetch.failed",
            module="services.market_chart",
            symbol=symbol,
            timeframe=tf,
            error_kind=info.kind,
            retryable=info.retryable,
        )
        if cached:
            return {
                **cached[1],
                "stale": True,
                "last_success_at": cached[2],
                "ttl_seconds": _CHART_TTL,
                "error": info.model_dump(),
            }
        return {
            "symbol": symbol,
            "base": base_u,
            "timeframe": tf,
            "bars": [],
            "stale": False,
            "last_success_at": None,
            "ttl_seconds": _CHART_TTL,
            "error": info.model_dump(),
        }
    if len(candles) < 50:
        payload = {
            "symbol": symbol,
            "base": base_u,
            "timeframe": tf,
            "bars": [],
            "stale": False,
            "last_success_at": None,
            "ttl_seconds": _CHART_TTL,
            "error": "Histórico insuficiente da Binance.",
        }
        return payload

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
    ind = add_indicators(df)
    tail = ind.tail(_DISPLAY_BARS)

    bars: list[dict] = []
    for ts, row in tail.iterrows():
        bars.append(
            {
                "t": int(ts.timestamp() * 1000),
                "o": _safe_float(row["open"]),
                "h": _safe_float(row["high"]),
                "l": _safe_float(row["low"]),
                "c": _safe_float(row["close"]),
                "ema20": _safe_float(row.get("ema20")),
                "ema200": _safe_float(row.get("ema200")),
                "bb_upper": _safe_float(row.get("bb_upper")),
                "bb_mid": _safe_float(row.get("bb_mid")),
                "bb_lower": _safe_float(row.get("bb_lower")),
                "supertrend": _safe_float(row.get("supertrend")),
            }
        )

    updated_at = pd.Timestamp.utcnow().isoformat()
    payload = {
        "symbol": symbol,
        "base": base_u,
        "timeframe": tf,
        "bars": bars,
        "indicators": ["ema20", "ema200", "bb_upper", "bb_mid", "bb_lower", "supertrend"],
        "updated_at": updated_at,
        "stale": False,
        "last_success_at": updated_at,
        "ttl_seconds": _CHART_TTL,
    }
    _CHART_CACHE[key] = (now, payload, updated_at)
    return payload
