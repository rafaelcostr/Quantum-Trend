"""Gráfico OHLCV do período simulado + marcadores de trades do backtest."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from atlas.core.config import load_config
from atlas.core.env import project_root
from atlas.core.symbols import build_symbol, validate_operated_base
from atlas.dashboard.actions import _apply_research_options
from atlas.research.collector import load_or_download
from atlas.research.reports import load_report_by_strategy_timeframe
from atlas.services.backtest_batch import resolve_backtest_config_path
from atlas.strategies.mm200_trend_v2 import strategy_display_name


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


def _parse_ts(raw: str | None) -> pd.Timestamp | None:
    if not raw:
        return None
    try:
        ts = pd.Timestamp(str(raw).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        return ts
    except (TypeError, ValueError):
        return None


def _bar_index_for_ts(index: pd.DatetimeIndex, ts: pd.Timestamp) -> int | None:
    if index.empty or ts is None:
        return None
    pos = int(index.searchsorted(ts, side="right")) - 1
    if pos < 0:
        pos = 0
    if pos >= len(index):
        pos = len(index) - 1
    return pos


def _trade_side(raw: dict[str, Any]) -> str:
    meta = raw.get("metadata") or {}
    side = str(meta.get("side") or raw.get("side") or "long").lower()
    if side in {"short", "sell", "bear"}:
        return "short"
    return "long"


def _markers_from_trades(trades: list[dict], index: pd.DatetimeIndex) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for i, raw in enumerate(trades):
        exit_time = raw.get("exit_time")
        if not exit_time:
            continue
        pnl = float(raw.get("pnl") or 0)
        raw_pct = float(raw.get("pnl_pct") or 0)
        pnl_pct = raw_pct * 100 if abs(raw_pct) <= 1 else raw_pct
        win = pnl > 0
        side = _trade_side(raw)

        entry_ts = _parse_ts(str(raw.get("entry_time") or ""))
        exit_ts = _parse_ts(str(exit_time))
        entry_idx = _bar_index_for_ts(index, entry_ts) if entry_ts is not None else None
        exit_idx = _bar_index_for_ts(index, exit_ts) if exit_ts is not None else None

        label = f"{pnl_pct:+.1f}%" if pnl_pct else f"{pnl:+.0f}"

        if entry_idx is not None:
            t_ms = int(index[entry_idx].timestamp() * 1000)
            markers.append(
                {
                    "t": t_ms,
                    "kind": "entry",
                    "side": side,
                    "win": win,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "price": _safe_float(raw.get("entry_price")),
                    "label": label,
                    "trade_index": i + 1,
                }
            )

        if exit_idx is not None and exit_idx != entry_idx:
            t_ms = int(index[exit_idx].timestamp() * 1000)
            markers.append(
                {
                    "t": t_ms,
                    "kind": "exit",
                    "side": side,
                    "win": win,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "price": _safe_float(raw.get("exit_price")),
                    "label": label,
                    "trade_index": i + 1,
                }
            )

    return markers


def get_backtest_chart_payload(
    *,
    strategy: str,
    timeframe: str,
    base: str = "BTC",
    quote: str = "USDT",
) -> dict[str, Any]:
    base_u = validate_operated_base(base)
    tf = timeframe.lower()
    symbol = build_symbol(base_u, quote)

    report = load_report_by_strategy_timeframe(strategy, tf, quote=quote, base=base_u)
    if not report:
        return {
            "symbol": symbol,
            "strategy": strategy,
            "strategy_label": strategy_display_name(strategy),
            "timeframe": tf,
            "base": base_u,
            "bars": [],
            "markers": [],
            "error": "Relatório não encontrado. Rode o backtest primeiro.",
        }

    meta = report.get("metadata") or {}
    config_rel = str(meta.get("config_file") or resolve_backtest_config_path(strategy, tf))
    config_path = project_root() / config_rel
    if not config_path.is_file():
        return {
            "symbol": symbol,
            "strategy": strategy,
            "strategy_label": strategy_display_name(strategy),
            "timeframe": tf,
            "base": base_u,
            "bars": [],
            "markers": [],
            "error": f"Config {config_rel} não encontrada.",
        }

    config = _apply_research_options(
        load_config(config_path),
        timeframe=tf,
        quote=quote,
        base_asset=base_u,
    )

    from atlas.strategies.registry import build_strategy_from_config

    strategy_impl = build_strategy_from_config(config.strategy.name, config.strategy.params)
    try:
        if getattr(strategy_impl, "uses_multi_timeframe", False):
            from atlas.quantum.multi_timeframe import build_execution_dataset

            df = build_execution_dataset(config)
        else:
            df = load_or_download(config)
    except Exception as exc:
        return {
            "symbol": symbol,
            "strategy": strategy,
            "strategy_label": strategy_display_name(strategy),
            "timeframe": tf,
            "base": base_u,
            "bars": [],
            "markers": [],
            "error": f"Sem dados OHLCV: {exc}",
        }

    if df.empty:
        return {
            "symbol": symbol,
            "strategy": strategy,
            "strategy_label": strategy_display_name(strategy),
            "timeframe": tf,
            "base": base_u,
            "bars": [],
            "markers": [],
            "error": "Histórico vazio. Baixe candles antes do backtest.",
        }

    warmup = int(config.strategy.params.get("warmup_bars", max(200, int(config.strategy.params.get("mm200_period", 200)) + 5)))
    warmup = min(warmup, max(0, len(df) - 1))
    sim = df.iloc[warmup:]

    bars: list[dict[str, Any]] = []
    for ts, row in sim.iterrows():
        bars.append(
            {
                "t": int(ts.timestamp() * 1000),
                "o": _safe_float(row["open"]),
                "h": _safe_float(row["high"]),
                "l": _safe_float(row["low"]),
                "c": _safe_float(row["close"]),
            }
        )

    trades = report.get("trades") or []
    markers = _markers_from_trades(trades, sim.index)
    metrics = report.get("metrics") or {}
    stats = report.get("statistics") or {}
    wins = sum(1 for t in trades if float(t.get("pnl") or 0) > 0)

    period_start = sim.index[0].isoformat() if len(sim) else None
    period_end = sim.index[-1].isoformat() if len(sim) else None

    return {
        "symbol": symbol,
        "strategy": strategy,
        "strategy_label": strategy_display_name(strategy),
        "timeframe": tf,
        "base": base_u,
        "period_start": period_start,
        "period_end": period_end,
        "bar_count": len(bars),
        "bars": bars,
        "markers": markers,
        "summary": {
            "trades": len(trades),
            "wins": wins,
            "losses": max(0, len(trades) - wins),
            "win_rate_pct": round(wins / len(trades) * 100, 1) if trades else 0.0,
            "total_return_pct": metrics.get("total_return_pct"),
            "profit_factor": metrics.get("profit_factor"),
            "max_drawdown_pct": metrics.get("max_drawdown_pct"),
            "atlas_score": metrics.get("atlas_score") or stats.get("atlas_score"),
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
