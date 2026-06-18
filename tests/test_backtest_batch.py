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
            on_progress(4, "Concluído")
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


def test_resolve_backtest_config_path_1d():
    from atlas.services.backtest_batch import resolve_backtest_config_path

    assert resolve_backtest_config_path("mm200_trend_v2", "1d") == "config/backtest_mm200_v2_1d.yaml"
    assert resolve_backtest_config_path("range_hunter_v1", "1d") == "config/backtest.yaml"


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
