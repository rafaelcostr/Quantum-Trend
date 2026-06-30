from __future__ import annotations

import time

from fastapi.testclient import TestClient

from atlas.api.main import create_app


def test_backtest_all_endpoint(monkeypatch):
    fake_summary = {
        "total_runs": 4,
        "completed": 4,
        "failed": 0,
        "timeframes": ["4h", "1d"],
        "quote": "USDT",
        "best": {
            "strategy": "mm200_trend_v2",
            "strategy_label": "MM200 Trend v2",
            "timeframe": "4h",
            "ok": True,
            "metrics": {"atlas_score": 72.0, "profit_factor": 1.5, "max_drawdown_pct": 8.0, "trades": 40},
        },
        "items": [
            {
                "strategy": "mm200_trend_v2",
                "strategy_label": "MM200 Trend v2",
                "timeframe": "4h",
                "ok": True,
                "metrics": {"atlas_score": 72.0},
            },
        ],
        "errors": [],
    }

    def fake_run(**kwargs):
        on_progress = kwargs.get("on_progress")
        if on_progress:
            on_progress(4, 4, "Concluído")
        return fake_summary

    monkeypatch.setattr("atlas.services.backtest_jobs.run_all_strategies_backtest", fake_run)
    monkeypatch.setattr(
        "atlas.services.terminal.clear_dashboard_cache",
        lambda: None,
    )
    monkeypatch.setattr(
        "atlas.services.terminal.clear_intelligence_cache",
        lambda: None,
    )

    client = TestClient(create_app())
    res = client.post("/api/backtest/all", json={"timeframes": ["4h", "1d"], "quote": "USDT"})
    assert res.status_code == 200
    job_id = res.json()["job_id"]
    assert job_id

    body = None
    for _ in range(50):
        status = client.get(f"/api/backtest/all/{job_id}")
        assert status.status_code == 200
        payload = status.json()
        if payload["status"] == "done":
            body = payload
            break
        time.sleep(0.05)
    assert body is not None
    assert body["total_runs"] == 4
    assert body["best"]["strategy"] == "mm200_trend_v2"


def test_list_backtest_matrix_includes_bear_strategies():
    from atlas.strategies.metadata import BACKTEST_MATRIX_GROUPS, list_backtest_matrix_strategies

    names = list_backtest_matrix_strategies()
    assert len(names) == 15
    assert "pullback_short_v1" in names
    assert "breakout_down_v1" in names
    assert "supertrend_bear_v1" in names
    assert len(BACKTEST_MATRIX_GROUPS["bear"]) == 3
    assert len(BACKTEST_MATRIX_GROUPS["bull"]) == 8
    assert len(BACKTEST_MATRIX_GROUPS["range"]) == 4


def test_matrix_groups_payload():
    from atlas.services.backtest_batch import _matrix_groups_payload, _strategy_rankings

    items = [
        {
            "strategy": "pullback_ema20_v1",
            "metrics": {"total_return_pct": 10.0},
        },
        {
            "strategy": "pullback_short_v1",
            "metrics": {"total_return_pct": 5.0},
        },
        {
            "strategy": "range_hunter_v1",
            "metrics": {"total_return_pct": 2.0},
        },
    ]
    groups = _matrix_groups_payload(items)
    assert len(groups) == 3
    assert groups[0]["market_type"] == "bull"
    assert groups[1]["market_type"] == "bear"
    assert groups[0]["total"] == 1
    assert groups[1]["items"][0]["strategy"] == "pullback_short_v1"
    rankings = _strategy_rankings([
        {**items[0], "ok": True, "metrics": {"total_return_pct": 10.0, "max_drawdown_pct": 12.0, "sharpe": 1.1, "stability_score": 60}},
        {**items[1], "ok": True, "metrics": {"total_return_pct": 5.0, "max_drawdown_pct": 4.0, "sharpe": 1.8, "stability_score": 80}},
    ])
    assert rankings["by_return"][0]["strategy"] == "pullback_ema20_v1"
    assert rankings["by_drawdown"][0]["strategy"] == "pullback_short_v1"
    assert rankings["by_stability"][0]["strategy"] == "pullback_short_v1"


def test_resolve_backtest_config_path_1d():
    from atlas.services.backtest_batch import resolve_backtest_config_path

    assert resolve_backtest_config_path("mm200_trend_v2", "1d") == "config/backtest_mm200_v2_1d.yaml"
    assert resolve_backtest_config_path("range_hunter_v1", "1d") == "config/backtest.yaml"


def test_quantum_backtest_does_not_crash_on_indicator_snapshot():
    """QuantumTrend Pro no backtest não deve montar IndicatorSnapshot.extra com pandas Series."""
    from unittest.mock import MagicMock

    import pandas as pd

    from atlas.core.config import load_config
    from atlas.core.env import project_root
    from atlas.core.models import Signal, SignalAction
    from atlas.research.engine_backtest import Backtester

    cfg = load_config(project_root() / "config" / "backtest_quantum_trend_pro.yaml")
    idx = pd.date_range("2024-01-01", periods=300, freq="1h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [100.0] * 300,
            "high": [101.0] * 300,
            "low": [99.0] * 300,
            "close": [100.5] * 300,
            "volume": [1000.0] * 300,
        },
        index=idx,
    )

    bt = Backtester(cfg, df)
    bt.strategy.build_context = lambda row, candle: MagicMock()
    bt.strategy.evaluate_context = lambda ctx, pos: Signal(action=SignalAction.HOLD, reason="test")
    result = bt.run()
    assert result.final_equity >= 0


def test_backtest_matrix_endpoint():
    from atlas.services.backtest_batch import load_backtest_matrix_from_reports

    client = TestClient(create_app())
    res = client.get("/api/backtest/matrix")
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert body["total"] == len(body["items"])
    disk = load_backtest_matrix_from_reports()
    assert body["total"] == disk["total"]
