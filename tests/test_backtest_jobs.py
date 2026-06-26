from __future__ import annotations

import json

import pytest

from atlas.services import backtest_jobs as jobs


@pytest.fixture(autouse=True)
def _reset_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "_jobs", {})
    monkeypatch.setattr(jobs, "_active_job_id", None)
    store = tmp_path / "backtest_job.json"
    monkeypatch.setattr(jobs, "_job_store_path", lambda: store)
    yield
    jobs.clear_backtest_job_cache()


def test_infer_base_asset_from_current():
    assert jobs._infer_base_asset({"current": "ETH · Pullback EMA20 v1 · 1H"}) == "ETH"
    assert jobs._infer_base_asset({"current": "Preparando matriz · BTC/USDT…"}) == "BTC"
    assert jobs._infer_base_asset({"current": "Pullback EMA20 v1 · 1H"}) == "BTC"


def test_recover_stale_persisted_job(tmp_path, monkeypatch):
    store = jobs._job_store_path()
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(
        json.dumps(
            {
                "id": "deadbeef0001",
                "status": "running",
                "total": 45,
                "completed": 3,
                "current": "Pullback EMA20 v1 · 1H",
            }
        ),
        encoding="utf-8",
    )

    jobs._recover_stale_persisted_job()

    raw = json.loads(store.read_text(encoding="utf-8"))
    assert raw["status"] == "error"
    assert "reiniciada" in raw["error"].lower()
    assert jobs.get_active_backtest_job() is None


def test_start_eth_after_stale_btc_job(monkeypatch):
    store = jobs._job_store_path()
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(
        json.dumps({"id": "oldjob", "status": "running", "total": 45, "completed": 1}),
        encoding="utf-8",
    )

    def fake_run(**kwargs):
        on_progress = kwargs.get("on_progress")
        if on_progress:
            on_progress(1, 45, "ETH · Pullback EMA20 v1 · 1H")
        return {"total_runs": 45, "completed": 1, "failed": 0, "items": [], "errors": []}

    monkeypatch.setattr(jobs, "run_all_strategies_backtest", fake_run)
    monkeypatch.setattr(
        "atlas.services.terminal.clear_dashboard_cache",
        lambda: None,
    )
    monkeypatch.setattr(
        "atlas.services.terminal.clear_intelligence_cache",
        lambda: None,
    )

    job_id = jobs.start_backtest_batch_job(timeframes=("1h",), quote="USDT", base_asset="ETH")
    job = jobs.get_backtest_batch_job(job_id)
    assert job is not None
    assert job.base_asset == "ETH"
    snap = jobs.job_snapshot(job)
    assert snap["asset_label"] == "ETH/USDT"


def test_block_eth_while_live_btc_running(monkeypatch):
    live = jobs.BacktestBatchJob(
        id="livebtc",
        status="running",
        total=45,
        base_asset="BTC",
        quote="USDT",
    )
    jobs._jobs["livebtc"] = live
    jobs._active_job_id = "livebtc"

    with pytest.raises(RuntimeError, match="BTC/USDT"):
        jobs.start_backtest_batch_job(timeframes=("1h",), quote="USDT", base_asset="ETH")
