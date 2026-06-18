"""Multi-Timeframe Engine — sincronização 1D / 4H / 1H."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from atlas.core.config import AtlasConfig
from atlas.core.models import Candle, IndicatorSnapshot
from atlas.core.indicators import add_indicators_from_params, row_to_indicator_snapshot
from atlas.quantum.models import MultiTimeframeContext, TimeframeSnapshot
from atlas.research.collector import load_or_download


QUANTUM_TIMEFRAMES = ("1d", "4h", "1h")
EXECUTION_TIMEFRAME = "1h"


def _config_for_timeframe(base: AtlasConfig, timeframe: str) -> AtlasConfig:
    cfg = base.model_copy(deep=True)
    cfg.exchange.timeframe = timeframe
    return cfg


def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        if "timestamp" in out.columns:
            out = out.set_index("timestamp")
    out.index = pd.to_datetime(out.index, utc=True)
    return out.sort_index()


def _quantum_indicator_params(params: dict) -> dict:
    merged = dict(params)
    merged.setdefault("ema_fast", 20)
    merged.setdefault("ema_slow", 200)
    merged["include_daily_macro"] = False
    ema_periods = sorted(set([
        int(merged.get("ema_fast", 20)),
        int(merged.get("ema_mid", 50)),
        int(merged.get("ema_slow", 200)),
    ]))
    merged["ema_periods_override"] = ema_periods
    return merged


def load_timeframe_frame(config: AtlasConfig, timeframe: str, params: dict) -> pd.DataFrame:
    cfg = _config_for_timeframe(config, timeframe)
    raw = load_or_download(cfg)
    raw = _ensure_datetime_index(raw)
    qparams = _quantum_indicator_params(params)
    qparams["ema_fast"] = 20 if timeframe != "1d" else 50
    if timeframe == "1d":
        qparams["ema_periods_override"] = [50, 200]
    elif timeframe == "4h":
        qparams["ema_periods_override"] = [20, 50]
    else:
        qparams["ema_periods_override"] = [20, 50, 200]
    return add_indicators_from_params(raw, qparams)


def merge_multi_timeframe_frames(
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame,
    df_1d: pd.DataFrame,
) -> pd.DataFrame:
    """Projeta indicadores 4H e 1D sobre o índice 1H (forward-fill)."""
    base = _ensure_datetime_index(df_1h)
    merged = base.copy()

    for prefix, source in (("h4", df_4h), ("d1", df_1d)):
        src = _ensure_datetime_index(source)
        numeric_cols = [
            c for c in src.columns
            if c not in {"open", "high", "low", "close", "volume"} and pd.api.types.is_numeric_dtype(src[c])
        ]
        aligned = src[numeric_cols].reindex(merged.index, method="ffill")
        aligned.columns = [f"{prefix}_{col}" for col in aligned.columns]
        merged = merged.join(aligned)

    merged["ema50_d1"] = merged.get("d1_ema50", merged.get("d1_ema20"))
    merged["ema200_d1"] = merged.get("d1_ema200")
    merged["adx_d1"] = merged.get("d1_adx")
    merged["ema20_h4"] = merged.get("h4_ema20")
    merged["ema50_h4"] = merged.get("h4_ema50", merged.get("h4_ema20"))
    merged["close_h4"] = merged.get("h4_close")
    return merged


def build_execution_dataset(config: AtlasConfig) -> pd.DataFrame:
    params = config.strategy.params
    df_1d = load_timeframe_frame(config, "1d", params)
    df_4h = load_timeframe_frame(config, "4h", params)
    df_1h = load_timeframe_frame(config, EXECUTION_TIMEFRAME, params)
    return merge_multi_timeframe_frames(df_1h, df_4h, df_1d)


@dataclass
class MultiTimeframeEngine:
    """Constrói contexto sincronizado a partir de uma linha do dataset merged."""

    def context_from_row(self, row: pd.Series, candle: Candle) -> MultiTimeframeContext:
        exec_snap = IndicatorSnapshot(
            timestamp=candle.timestamp,
            **{k: v for k, v in row_to_indicator_snapshot(row).items() if k != "macro_bull"},
        )
        macro_snap = _snapshot_from_prefixed(row, candle.timestamp, prefix="d1", fallback=exec_snap)
        confirm_snap = _snapshot_from_prefixed(row, candle.timestamp, prefix="h4", fallback=exec_snap)
        macro_candle = _candle_from_prefixed(row, candle.timestamp, prefix="d1", fallback=candle)
        confirm_candle = _candle_from_prefixed(row, candle.timestamp, prefix="h4", fallback=candle)
        return MultiTimeframeContext(
            execution=TimeframeSnapshot("1h", candle, exec_snap),
            confirm=TimeframeSnapshot("4h", confirm_candle, confirm_snap),
            macro=TimeframeSnapshot("1d", macro_candle, macro_snap),
        )


def _snapshot_from_row(row: pd.Series, ts, prefix: str = "") -> IndicatorSnapshot:
    snap = row_to_indicator_snapshot(row)
    return IndicatorSnapshot(timestamp=ts, **{k: v for k, v in snap.items() if k != "macro_bull"})


def _snapshot_from_prefixed(
    row: pd.Series,
    ts,
    *,
    prefix: str,
    fallback: IndicatorSnapshot,
) -> IndicatorSnapshot:
    mapping = {
        "ema20": f"{prefix}_ema20",
        "ema50": f"{prefix}_ema50",
        "ema200": f"{prefix}_ema200",
        "adx": f"{prefix}_adx",
        "atr": f"{prefix}_atr",
        "rsi": f"{prefix}_rsi",
        "close": f"{prefix}_close",
    }
    values: dict[str, float | None] = {}
    for target, source in mapping.items():
        if source in row and pd.notna(row[source]):
            values[target] = float(row[source])
        elif target == "ema50" and f"{prefix}_ema20" in row and pd.notna(row[f"{prefix}_ema20"]):
            values[target] = float(row[f"{prefix}_ema20"])
    if not values.get("ema200") and fallback.ema200 is not None:
        values.setdefault("ema200", fallback.ema200)
    if not values.get("ema50") and fallback.ema50 is not None:
        values.setdefault("ema50", fallback.ema50)
    return IndicatorSnapshot(
        timestamp=ts,
        adx=values.get("adx"),
        atr=values.get("atr"),
        rsi=values.get("rsi"),
        ema20=values.get("ema20"),
        ema50=values.get("ema50"),
        ema200=values.get("ema200"),
        extra={"close": values.get("close")} if values.get("close") else {},
    )


def _candle_from_prefixed(row: pd.Series, ts, *, prefix: str, fallback: Candle) -> Candle:
    def _col(name: str, default: float) -> float:
        key = f"{prefix}_{name}"
        if key in row and pd.notna(row[key]):
            return float(row[key])
        return default

    return Candle(
        timestamp=ts,
        open=_col("open", fallback.open),
        high=_col("high", fallback.high),
        low=_col("low", fallback.low),
        close=_col("close", fallback.close),
        volume=_col("volume", fallback.volume),
    )
