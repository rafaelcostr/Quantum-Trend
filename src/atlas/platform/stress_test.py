"""Stress Test Engine — cenários extremos offline."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from atlas.platform.models import StressTestReport
from atlas.platform.store import load_platform_state, save_platform_state


def _simulate_gap(df: pd.DataFrame, gap_pct: float) -> pd.DataFrame:
    out = df.copy()
    if len(out) < 2:
        return out
    idx = len(out) // 2
    out.iloc[idx, out.columns.get_loc("open")] *= 1 + gap_pct
    out.iloc[idx:, out.columns.get_loc("close")] *= 1 + gap_pct
    out.iloc[idx:, out.columns.get_loc("high")] *= 1 + gap_pct
    out.iloc[idx:, out.columns.get_loc("low")] *= 1 + gap_pct
    return out


def _max_drawdown(equity: np.ndarray) -> float:
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / np.maximum(peak, 1e-9)
    return float(np.max(dd) * 100)


def run_stress_scenario(name: str, df: pd.DataFrame, *, gap_pct: float = 0.0, slippage_bps: float = 0.0) -> StressTestReport:
    sim = _simulate_gap(df, gap_pct) if gap_pct else df.copy()
    closes = sim["close"].astype(float).values
    if slippage_bps:
        closes = closes * (1 - slippage_bps / 10000)

    returns = np.diff(closes) / closes[:-1]
    equity = np.cumprod(1 + returns) * 10000
    mdd = _max_drawdown(equity)
    survived = mdd < 35 and not np.isnan(equity).any()

    summary = (
        f"Cenário {name}: drawdown máximo {mdd:.1f}% — "
        + ("sistema sobreviveria com gestão de risco." if survived else "risco de stop diário/semana.")
    )
    report = StressTestReport(
        scenario=name,
        survived=survived,
        summary=summary,
        metrics={"max_drawdown_pct": round(mdd, 2), "gap_pct": gap_pct, "slippage_bps": slippage_bps},
        ts=datetime.now(timezone.utc).isoformat(),
    )
    return report


def run_default_stress_suite(df: pd.DataFrame | None = None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        idx = pd.date_range("2024-01-01", periods=200, freq="1D", tz="UTC")
        rng = np.random.default_rng(42)
        price = 100 * np.cumprod(1 + rng.normal(0.001, 0.02, len(idx)))
        df = pd.DataFrame(
            {
                "open": price,
                "high": price * 1.01,
                "low": price * 0.99,
                "close": price,
                "volume": rng.uniform(100, 1000, len(idx)),
            },
            index=idx,
        )

    scenarios = [
        ("gap_-10pct", -0.10, 0),
        ("gap_-20pct", -0.20, 0),
        ("slippage_alto", 0, 50),
        ("gap_e_slippage", -0.15, 30),
        ("volatilidade_extrema", -0.08, 20),
    ]
    reports = [run_stress_scenario(name, df, gap_pct=gap, slippage_bps=slip).to_dict() for name, gap, slip in scenarios]

    data = load_platform_state()
    data["stress_reports"] = reports
    save_platform_state(data)
    return reports
