from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from atlas.api.main import create_app
from atlas.services.balance_history import load_balance_curve, record_balance
from atlas.core.models import TradingMode


def test_health():
    client = TestClient(create_app())
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "bot_mode" in body


def test_dashboard_endpoint():
    client = TestClient(create_app())
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert "stats" in body
    assert "equity_curve" in body
    assert body["stats"]["balance_source"] in {
        "binance_demo",
        "binance_live",
        "api_error",
        "unavailable",
        "unknown",
    }


def test_operations_feed_endpoint():
    client = TestClient(create_app())
    res = client.get("/api/operations/feed")
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert "bot" in body
    assert body["mode"] in ("paper", "live")


def test_live_gates_endpoint():
    client = TestClient(create_app())
    res = client.get("/api/live/gates")
    assert res.status_code == 200
    body = res.json()
    assert "eligible" in body
    assert "checks" in body


def test_live_view_endpoint():
    client = TestClient(create_app())
    res = client.get("/api/live")
    assert res.status_code == 200
    body = res.json()
    assert "gates" in body
    assert "config" in body


def test_markets_endpoint(monkeypatch):
    from atlas.core.models import MarketTicker

    client = TestClient(create_app())
    monkeypatch.setattr(
        "atlas.services.terminal.fetch_tickers_cached",
        lambda **kwargs: [
            MarketTicker(symbol="BTC", price=100_000.0, change_pct=1.5, volume_24h=1e9, sparkline=[1, 2, 3]),
        ],
    )
    res = client.get("/api/markets")
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["symbol"] == "BTC"


def test_intelligence_endpoint(monkeypatch):
    client = TestClient(create_app())
    monkeypatch.setattr(
        "atlas.services.terminal.fetch_tickers_cached",
        lambda **kwargs: [],
    )
    res = client.get("/api/intelligence")
    assert res.status_code == 200
    body = res.json()
    assert "strategies_evaluated" in body
    assert "heatmap" in body


def test_walkforward_endpoint(monkeypatch):
    client = TestClient(create_app())

    def _fake_wf(config_path: str, train_pct: float = 0.70):
        return Path("data/reports/mm200_trend_v1_walkforward.json")

    monkeypatch.setattr(
        "atlas.research.backtester.run_walkforward_from_yaml",
        _fake_wf,
    )
    res = client.post("/api/research/walkforward", json={"config_path": "config/backtest_mm200_v2.yaml"})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert "report_path" in body


def test_balance_history_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "atlas.services.balance_history.project_root",
        lambda: tmp_path,
    )
    record_balance(mode=TradingMode.PAPER, equity=10_000.0, symbol="BTC/USDT")
    record_balance(mode=TradingMode.PAPER, equity=10_050.0, symbol="BTC/USDT")
    curve = load_balance_curve(mode=TradingMode.PAPER)
    assert len(curve) == 2
    assert curve[-1]["equity"] == 10_050.0
