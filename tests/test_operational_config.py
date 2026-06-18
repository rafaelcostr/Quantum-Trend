from __future__ import annotations

from fastapi.testclient import TestClient

from atlas.api.main import create_app
from atlas.runtime.operational_config import load_active_paper_config, poll_seconds_for_timeframe, save_operational_selection


def test_poll_seconds_for_timeframe():
    assert poll_seconds_for_timeframe("1h") == 15
    assert poll_seconds_for_timeframe("4h") == 30
    assert poll_seconds_for_timeframe("1d") == 3600


def test_save_operational_1d(tmp_path, monkeypatch):
    monkeypatch.setattr("atlas.runtime.operational_config.project_root", lambda: tmp_path)
    monkeypatch.setattr("atlas.core.config.project_root", lambda: tmp_path)
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "paper.yaml").write_text(
        """
mode: paper
exchange:
  id: binance
  symbol: BTC/USDT
  timeframe: 4h
  demo: true
strategy:
  name: mm200_trend_v2
  params: {}
risk:
  initial_capital: 10000
runtime:
  poll_seconds: 30
""",
        encoding="utf-8",
    )
    (tmp_path / "config" / "live.yaml").write_text(
        (tmp_path / "config" / "paper.yaml").read_text(encoding="utf-8").replace("paper", "live"),
        encoding="utf-8",
    )
    (tmp_path / "config" / "backtest_mm200_v2.yaml").write_text(
        (tmp_path / "config" / "paper.yaml").read_text(encoding="utf-8").replace("paper", "backtest"),
        encoding="utf-8",
    )

    cfg = save_operational_selection(strategy_name="mm200_trend_v2", timeframe="1d", quote_asset="USDT")
    assert cfg.exchange.timeframe == "1d"
    assert cfg.runtime.poll_seconds == 3600
    loaded = load_active_paper_config()
    assert loaded.strategy.name == "mm200_trend_v2"
    assert loaded.exchange.timeframe == "1d"


def test_settings_operational_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr("atlas.runtime.operational_config.project_root", lambda: tmp_path)
    monkeypatch.setattr("atlas.core.config.project_root", lambda: tmp_path)
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "paper.yaml").write_text(
        "mode: paper\nexchange:\n  id: binance\n  symbol: BTC/USDT\n  timeframe: 4h\n  demo: true\nstrategy:\n  name: mm200_trend_v2\n  params: {}\nrisk:\n  initial_capital: 10000\nruntime:\n  poll_seconds: 30\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "live.yaml").write_text(
        "mode: live\nexchange:\n  id: binance\n  symbol: BTC/USDT\n  timeframe: 4h\n  demo: false\nstrategy:\n  name: mm200_trend_v2\n  params: {}\nrisk:\n  initial_capital: 10000\nruntime:\n  poll_seconds: 30\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "backtest_mm200_v2.yaml").write_text(
        "mode: backtest\nexchange:\n  id: binance\n  symbol: BTC/USDT\n  timeframe: 4h\n  demo: true\nstrategy:\n  name: mm200_trend_v2\n  params: {}\nrisk:\n  initial_capital: 10000\n",
        encoding="utf-8",
    )

    client = TestClient(create_app())
    res = client.put(
        "/api/settings/operational",
        json={"strategy": "mm200_trend_v2", "timeframe": "1d", "quote": "USDT"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["system"]["timeframe"] == "1d"
    assert body["system"]["poll_seconds"] == 3600


def test_kill_switch_endpoint():
    client = TestClient(create_app())
    res = client.put("/api/settings/kill-switch", json={"active": True})
    assert res.status_code == 200
    assert res.json()["system"]["kill_switch"] is True
    res2 = client.put("/api/settings/kill-switch", json={"active": False})
    assert res2.json()["system"]["kill_switch"] is False
