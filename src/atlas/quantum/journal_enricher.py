"""Journal automático enriquecido — motivos, score e regime."""
from __future__ import annotations

from typing import Any

from atlas.core.models import Candle, Position, Signal
from atlas.quantum.models import MultiTimeframeContext


def build_trade_journal_payload(
    *,
    event: str,
    signal: Signal,
    candle: Candle,
    ctx: MultiTimeframeContext | None = None,
    position: Position | None = None,
    indicators: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = dict(signal.metadata or {})
    payload: dict[str, Any] = {
        "event_type": event,
        "reason": signal.reason,
        "signal": signal.action.value,
        "alignment_score": meta.get("alignment_score"),
        "alignment_breakdown": meta.get("alignment_breakdown"),
        "regime": meta.get("regime"),
        "regime_label": meta.get("regime_label"),
        "entry_module": meta.get("entry_module"),
        "entry_confidence": meta.get("entry_confidence"),
        "entry_indicators": meta.get("entry_indicators"),
        "rejected_modules": meta.get("rejected_modules"),
        "module_status": meta.get("module_status"),
        "risk_profile": meta.get("risk_profile"),
        "stop_price": signal.stop_price,
        "target_price": signal.target_price,
        "candle": {
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
            "timestamp": candle.timestamp.isoformat(),
        },
        "indicators": indicators or _indicators_from_context(ctx),
    }
    if position is not None:
        payload["position"] = {
            "entry_price": position.entry_price,
            "quantity": position.quantity,
            "stop_price": position.stop_price,
            "target_price": position.target_price,
        }
    return payload


def _indicators_from_context(ctx: MultiTimeframeContext | None) -> dict[str, Any]:
    if ctx is None:
        return {}
    exec_ind = ctx.execution.indicators
    macro = ctx.macro.indicators if ctx.macro else None
    confirm = ctx.confirm.indicators if ctx.confirm else None
    return {
        "1h": {
            "rsi": exec_ind.rsi,
            "adx": exec_ind.adx,
            "atr": exec_ind.atr,
            "ema20": exec_ind.ema20,
            "ema50": exec_ind.ema50,
            "ema200": exec_ind.ema200,
        },
        "4h": {
            "ema20": confirm.ema20 if confirm else None,
            "ema50": confirm.ema50 if confirm else None,
        },
        "1d": {
            "ema50": macro.ema50 if macro else None,
            "ema200": macro.ema200 if macro else None,
            "adx": macro.adx if macro else None,
        },
    }
