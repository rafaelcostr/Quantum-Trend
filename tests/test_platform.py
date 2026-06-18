from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from atlas.platform.data_quality import assess_dataframe
from atlas.platform.score_explanation import build_score_explanation
from atlas.platform.state_machine import PlatformState, can_execute_event, transition
from atlas.platform.store import acknowledge_risk_lock, load_platform_state, set_risk_locked
from atlas.platform.stress_test import run_stress_scenario
from atlas.platform.trend_exhaustion import detect_trend_exhaustion


def test_data_quality_clean_series():
    idx = pd.date_range("2024-01-01", periods=100, freq="1D", tz="UTC")
    rng = np.random.default_rng(1)
    close = 100 + rng.normal(0, 1, len(idx)).cumsum()
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": rng.uniform(10, 100, len(idx)),
        },
        index=idx,
    )
    report = assess_dataframe(df, timeframe="1d", source="test")
    assert report.score >= 70
    assert report.ok is True


def test_score_explanation_components():
    explanation = build_score_explanation(
        total=87,
        breakdown={
            "trend_alignment": 35,
            "adx_strength": 18,
            "volume_confirmation": 12,
            "volatility_regime": 12,
            "momentum_confirmation": 10,
        },
        threshold=80,
    )
    assert explanation["total"] == 87
    assert len(explanation["components"]) == 5
    assert explanation["eligible"] is True


def test_trend_exhaustion_high_rsi():
    row = pd.Series({"close": 110, "rsi": 78, "ema20": 100, "ema50": 95, "adx": 28, "atr": 2})
    result = detect_trend_exhaustion(row)
    assert result.exhausted is True


def test_stress_gap_scenario():
    idx = pd.date_range("2024-01-01", periods=50, freq="1D", tz="UTC")
    price = np.linspace(100, 120, len(idx))
    df = pd.DataFrame(
        {"open": price, "high": price + 1, "low": price - 1, "close": price, "volume": 100},
        index=idx,
    )
    report = run_stress_scenario("gap_-10pct", df, gap_pct=-0.10)
    assert "drawdown" in report.summary.lower() or report.metrics["max_drawdown_pct"] >= 0


def test_state_machine_risk_locked_blocks_trade(monkeypatch, tmp_path):
    monkeypatch.setattr("atlas.platform.store._STORE_PATH", tmp_path / "platform_state.json")
    transition(PlatformState.RISK_LOCKED, "teste", force=True)
    assert can_execute_event("trade") is False
    set_risk_locked(True, "inconsistência")
    assert acknowledge_risk_lock() is True
    assert load_platform_state().get("risk_locked") is False
