"""Detecção de regime operacional (Alta / Baixa / Lateral) para o dashboard."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import pandas as pd

from atlas.brokers.binance import fetch_public_candles
from atlas.core.config import AtlasConfig
from atlas.core.indicators import add_indicators_from_params, row_to_indicator_snapshot
from atlas.core.models import Candle, IndicatorSnapshot
from atlas.runtime.operational_config import load_paper_slots
from atlas.runtime.state import active_config
from atlas.strategies.market_orchestrator import detect_execution_regime, regime_allows_market_type
from atlas.strategies.metadata import backtest_matrix_group_labels, get_market_type
from atlas.strategies.mm200_trend_v2 import strategy_display_name

REGIME_LABELS_PT: dict[str, str] = {
    "bull": "Alta",
    "bear": "Baixa",
    "range": "Lateral",
}

REGIME_ROUTES: dict[str, str] = {
    "bull": "/estrategias-alta",
    "bear": "/estrategias-baixa",
    "range": "/estrategias-lateral",
}

REGIME_SUGGESTIONS: dict[str, str] = {
    "bull": "Use Estratégias de Alta — Pullback, Breakout, Supertrend Long ou QuantumTrend Pro.",
    "bear": "Use Estratégias de Baixa — Pullback Short, Breakout Down ou Supertrend Bear.",
    "range": "Use Estratégias Laterais — Range Hunter, BB Squeeze ou Regime Switching.",
}

REGIME_ACCENT: dict[str, str] = {
    "bull": "success",
    "bear": "destructive",
    "range": "warning",
}

_REGIME_CACHE: dict[tuple[str, str], tuple[float, dict]] = {}
_REGIME_TTL = 120.0


def explain_execution_regime(candle: Candle, indicators: IndicatorSnapshot) -> str:
    """Texto legível alinhado à lógica de detect_execution_regime."""
    if indicators.ema200 is None or indicators.adx is None:
        return "Indicadores insuficientes — aguardando warmup (EMA200 / ADX)."

    adx = float(indicators.adx)
    close = float(candle.close)
    ema200 = float(indicators.ema200)

    if adx < 15:
        return f"ADX {adx:.1f} < 15 — mercado lateral, sem tendência forte."

    if close > ema200 and adx >= 20:
        return f"Preço ${close:,.2f} acima da EMA200 (${ema200:,.2f}) com ADX {adx:.1f} — tendência de alta."

    if close < ema200 and adx >= 20:
        return f"Preço ${close:,.2f} abaixo da EMA200 (${ema200:,.2f}) com ADX {adx:.1f} — tendência de baixa."

    side = "acima" if close >= ema200 else "abaixo"
    return (
        f"Preço {side} da EMA200, mas ADX {adx:.1f} entre 15–20 — "
        "regime lateral ou transição."
    )


def _candle_from_row(row: pd.Series, ts) -> Candle:
    return Candle(
        timestamp=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        volume=float(row["volume"]),
    )


def _slot_alignment(regime: str) -> dict:
    enabled = [s for s in load_paper_slots() if s.enabled]
    slots: list[dict] = []
    matching = 0
    for slot in enabled:
        market_type = get_market_type(slot.strategy)
        allowed = regime_allows_market_type(regime, market_type)
        if allowed:
            matching += 1
        slots.append(
            {
                "strategy": slot.strategy,
                "strategy_label": strategy_display_name(slot.strategy),
                "timeframe": slot.timeframe.lower(),
                "market_type": market_type,
                "operates_now": allowed,
            }
        )
    group_labels = backtest_matrix_group_labels()
    active_types = sorted({s["market_type"] for s in slots})
    return {
        "enabled_count": len(enabled),
        "matching_count": matching,
        "aligned_with_bot": matching > 0 if enabled else True,
        "active_market_types": active_types,
        "active_market_labels": [group_labels.get(t, t) for t in active_types],
        "slots": slots,
        "warning": (
            None
            if not enabled or matching > 0
            else f"Nenhum slot habilitado opera no regime {REGIME_LABELS_PT.get(regime, regime)}."
        ),
    }


def get_market_regime_snapshot(cfg: AtlasConfig | None = None) -> dict:
    """Calcula regime atual a partir do símbolo/timeframe ativos."""
    cfg = cfg or active_config()
    symbol = cfg.exchange.symbol
    timeframe = cfg.exchange.timeframe.lower()
    cache_key = (symbol, timeframe)
    now = time.time()
    cached = _REGIME_CACHE.get(cache_key)
    if cached and (now - cached[0]) < _REGIME_TTL:
        return cached[1]

    base = {
        "available": False,
        "symbol": symbol,
        "timeframe": timeframe,
        "market_type": "range",
        "label": REGIME_LABELS_PT["range"],
        "suggestion": REGIME_SUGGESTIONS["range"],
        "strategies_route": REGIME_ROUTES["range"],
        "accent": REGIME_ACCENT["range"],
        "reason": "Aguardando dados de mercado.",
        "close": None,
        "ema200": None,
        "adx": None,
        "price_vs_ema_pct": None,
        "candle_at": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "aligned_with_bot": True,
        "enabled_slots": 0,
        "matching_slots": 0,
        "active_market_types": [],
        "active_market_labels": [],
        "slot_details": [],
        "warning": None,
        "error": None,
    }

    try:
        candles = fetch_public_candles(symbol, timeframe, limit=500)
    except Exception as exc:
        base["error"] = str(exc)[:240]
        base["reason"] = "Não foi possível obter candles da Binance (rede ou símbolo)."
        _REGIME_CACHE[cache_key] = (now, base)
        return base

    if len(candles) < 210:
        base["error"] = f"Poucos candles ({len(candles)}) para EMA200."
        base["reason"] = "Histórico insuficiente para calcular EMA200."
        _REGIME_CACHE[cache_key] = (now, base)
        return base

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
    ind_df = add_indicators_from_params(df, cfg.strategy.params or {})
    row = ind_df.iloc[-1]
    candle = _candle_from_row(row, ind_df.index[-1])
    snap = row_to_indicator_snapshot(row)
    indicators = IndicatorSnapshot(timestamp=candle.timestamp, **snap)

    regime = detect_execution_regime(candle, indicators)
    alignment = _slot_alignment(regime)
    close = float(candle.close)
    ema200 = indicators.ema200
    adx = indicators.adx
    vs_ema = round(((close / ema200) - 1) * 100, 2) if ema200 else None

    base.update(
        {
            "available": True,
            "market_type": regime,
            "label": REGIME_LABELS_PT[regime],
            "suggestion": REGIME_SUGGESTIONS[regime],
            "strategies_route": REGIME_ROUTES[regime],
            "accent": REGIME_ACCENT[regime],
            "reason": explain_execution_regime(candle, indicators),
            "close": round(close, 2),
            "ema200": round(float(ema200), 2) if ema200 is not None else None,
            "adx": round(float(adx), 2) if adx is not None else None,
            "price_vs_ema_pct": vs_ema,
            "candle_at": candle.timestamp.isoformat(),
            "aligned_with_bot": alignment["aligned_with_bot"],
            "enabled_slots": alignment["enabled_count"],
            "matching_slots": alignment["matching_count"],
            "active_market_types": alignment["active_market_types"],
            "active_market_labels": alignment["active_market_labels"],
            "slot_details": alignment["slots"],
            "warning": alignment["warning"],
        }
    )
    _REGIME_CACHE[cache_key] = (now, base)
    return base
