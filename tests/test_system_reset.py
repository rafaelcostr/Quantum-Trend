from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from atlas.api.main import create_app
from atlas.services.system_reset import ResetOptions, reset_system_data


@pytest.fixture
def isolated_data(tmp_path: Path, monkeypatch):
    data = tmp_path / "data"
    (data / "reports").mkdir(parents=True)
    (data / "cache").mkdir(parents=True)
    (data / "journal").mkdir(parents=True)
    (data / "runtime").mkdir(parents=True)

    report = data / "reports" / "mm200_trend_v2_1d_usdt_report.json"
    report.write_text('{"statistics": {}}', encoding="utf-8")
    cache = data / "cache" / "binance_BTCUSDT_1d.csv"
    cache.write_text("timestamp,open\n", encoding="utf-8")
    journal = data / "journal" / "paper.jsonl"
    journal.write_text('{"event":"tick"}\n', encoding="utf-8")

    monkeypatch.setattr("atlas.services.system_reset.project_root", lambda: tmp_path)
    monkeypatch.setattr("atlas.runtime.risk_store.project_root", lambda: tmp_path)
    monkeypatch.setattr("atlas.runtime.risk_store._PATH", data / "runtime" / "risk.json")
    monkeypatch.setattr("atlas.runtime.risk_store._store", None)
    return data


def test_reset_reports_only(isolated_data: Path):
    result = reset_system_data(ResetOptions(reports=True))
    assert len(result.deleted_files) == 1
    assert not (isolated_data / "reports" / "mm200_trend_v2_1d_usdt_report.json").exists()
    assert (isolated_data / "cache" / "binance_BTCUSDT_1d.csv").exists()


def test_reset_api_endpoint(isolated_data: Path, monkeypatch):
    monkeypatch.setattr("atlas.services.system_reset.project_root", lambda: isolated_data.parent)
    client = TestClient(create_app())
    res = client.post("/api/system/reset", json={"reports": True, "ohlcv_cache": False, "paper_demo": False})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["deleted_count"] >= 1


def test_reset_requires_option():
    client = TestClient(create_app())
    res = client.post("/api/system/reset", json={"reports": False, "ohlcv_cache": False, "paper_demo": False})
    assert res.status_code == 400
