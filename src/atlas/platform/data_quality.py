"""Data Quality Monitor — integridade de candles e indicadores."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from atlas.platform.models import DataQualityReport
from atlas.platform.store import patch_platform_state

_TF_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}


def _expected_gap_minutes(timeframe: str) -> float:
    return float(_TF_MINUTES.get(timeframe.lower(), 60))


def assess_dataframe(df: pd.DataFrame, *, timeframe: str, source: str = "live") -> DataQualityReport:
    issues: list[str] = []
    score = 100.0

    if df is None or df.empty:
        return DataQualityReport(score=0, issues=["dataframe vazio"], candle_count=0, last_candle_ts=None, ok=False)

    required = {"open", "high", "low", "close"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        issues.append(f"colunas ausentes: {', '.join(sorted(missing_cols))}")
        score -= 40

    candle_count = len(df)
    if candle_count < 50:
        issues.append(f"poucos candles ({candle_count})")
        score -= 15

    last_ts: str | None = None
    if isinstance(df.index, pd.DatetimeIndex) and len(df.index):
        last_ts = df.index[-1].isoformat()
        age_min = (datetime.now(timezone.utc) - df.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)).total_seconds() / 60
        max_age = _expected_gap_minutes(timeframe) * 3
        if age_min > max_age:
            issues.append(f"último candle desatualizado ({int(age_min)} min)")
            score -= 20

    if len(df.index) >= 3 and isinstance(df.index, pd.DatetimeIndex):
        gaps = df.index.to_series().diff().dropna()
        expected = pd.Timedelta(minutes=_expected_gap_minutes(timeframe))
        large_gaps = gaps[gaps > expected * 2]
        if len(large_gaps) > 0:
            issues.append(f"buracos temporais detectados ({len(large_gaps)})")
            score -= min(25, len(large_gaps) * 2)

    for col in ("open", "high", "low", "close"):
        if col not in df.columns:
            continue
        if df[col].isna().any():
            issues.append(f"NaN em {col}")
            score -= 10
        if np.isinf(df[col]).any():
            issues.append(f"infinito em {col}")
            score -= 10
        invalid = (df["high"] < df["low"]) | (df["close"] > df["high"]) | (df["close"] < df["low"])
        if invalid.any():
            issues.append("OHLC inválido detectado")
            score -= 15
            break

    if "volume" in df.columns:
        zero_vol = int((df["volume"] <= 0).sum())
        if zero_vol > candle_count * 0.05:
            issues.append(f"volume zerado em {zero_vol} candles")
            score -= 10

    indicator_cols = [c for c in df.columns if c not in {"open", "high", "low", "close", "volume"}]
    for col in indicator_cols[:12]:
        if df[col].isna().tail(5).all():
            continue
        if df[col].isna().tail(1).any():
            issues.append(f"indicador {col} NaN no último candle")
            score -= 5
        if np.isinf(df[col].tail(1)).any():
            issues.append(f"indicador {col} infinito")
            score -= 5

    score = max(0.0, min(100.0, round(score, 1)))
    ok = score >= 70 and not any("dataframe vazio" in i or "OHLC inválido" in i for i in issues)

    report = DataQualityReport(
        score=score,
        issues=issues,
        candle_count=candle_count,
        last_candle_ts=last_ts,
        ok=ok,
    )
    patch_platform_state(
        data_quality={
            **report.to_dict(),
            "source": source,
            "timeframe": timeframe,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return report


def assess_cache_file(path: str | Any) -> DataQualityReport:
    from pathlib import Path

    p = Path(path)
    if not p.is_file():
        return DataQualityReport(score=0, issues=["cache ausente ou corrompido"], candle_count=0, last_candle_ts=None, ok=False)
    try:
        df = pd.read_csv(p, parse_dates=["timestamp"], index_col="timestamp")
        tf = "1d" if "1d" in p.stem else "4h" if "4h" in p.stem else "1h"
        return assess_dataframe(df, timeframe=tf, source=str(p.name))
    except Exception as exc:
        return DataQualityReport(score=0, issues=[f"cache corrompido: {exc}"], candle_count=0, last_candle_ts=None, ok=False)
