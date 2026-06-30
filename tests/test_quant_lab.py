from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from atlas.api.main import app
from atlas.services import quant_lab


def _sample_report(strategy: str = "range_hunter_v2", timeframe: str = "4h") -> dict:
    return {
        "metadata": {
            "strategy": strategy,
            "strategy_version": "2.0.0",
            "strategy_type": "Mean Reversion",
            "market": "BTC/USDT",
            "base_asset": "BTC",
            "quote": "USDT",
            "timeframe": timeframe,
            "config_file": "config/backtest_v2.yaml",
            "mode": "backtest",
            "risk_model": "risk_based",
            "position_size": "1% per trade",
            "risk_per_trade": 0.01,
            "fee_rate": 0.001,
            "slippage_rate": 0.0005,
            "initial_capital": 10000,
            "generated_at": "2024-06-01T00:00:00+00:00",
        },
        "statistics": {
            "net_profit_pct": 0.12,
            "max_drawdown_pct": 0.08,
            "profit_factor": 1.7,
            "sharpe_ratio": 1.3,
            "win_rate": 0.58,
            "total_trades": 12,
        },
        "trades": [
            {
                "entry_time": "2024-01-02T00:00:00+00:00",
                "exit_time": "2024-01-03T00:00:00+00:00",
                "entry_price": 41000,
                "exit_price": 41500,
                "pnl": 100,
                "pnl_pct": 0.01,
                "metadata": {"entry_reason": "rompimento confirmado", "rsi": 54},
            }
        ],
        "equity_curve": [
            {"timestamp": "2024-01-01T00:00:00+00:00", "equity": 10000},
            {"timestamp": "2024-01-02T00:00:00+00:00", "equity": 10080},
            {"timestamp": "2024-01-03T00:00:00+00:00", "equity": 10120},
        ],
    }


def _write_report(root: Path, name: str, payload: dict) -> Path:
    reports = root / "data" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_quant_lab_versions_annotations_compare_and_replay(tmp_path: Path):
    _write_report(tmp_path, "range_hunter_v2_4h_usdt_btc_report.json", _sample_report())
    _write_report(tmp_path, "mm200_trend_v2_1d_usdt_btc_report.json", _sample_report("mm200_trend_v2", "1d"))

    payload = quant_lab.list_experiments(root=tmp_path)
    assert payload["total"] == 2
    first_id = payload["items"][0]["id"]
    second_id = payload["items"][1]["id"]
    assert payload["items"][0]["parameters"]["config_file"]
    assert payload["items"][0]["period_start"] == "2024-01-01"
    assert payload["items"][0]["metrics"]["total_return_pct"] == 12.0

    ann = quant_lab.update_experiment_annotation(
        first_id,
        tags=["promissor", "overfit", "tag-invalida"],
        note="boa hipotese",
        root=tmp_path,
    )
    assert ann["annotation"]["tags"] == ["promissor", "overfit"]

    comparison = quant_lab.compare_experiments([first_id, second_id], root=tmp_path)
    assert len(comparison["equity_curves"]) == 2
    assert comparison["best_id"] in {first_id, second_id}

    replay = quant_lab.strategy_replay(first_id, root=tmp_path)
    assert replay["total_events"] == 3
    assert any(ev["signal"] == "entry" and ev["reason"] == "rompimento confirmado" for ev in replay["events"])

    library = quant_lab.strategy_library(root=tmp_path)
    ids = {item["id"] for item in library["items"]}
    assert "range_hunter_v2" in ids
    updated = quant_lab.update_strategy_status("range_hunter_v2", status="active", root=tmp_path)
    assert updated["strategy"]["status"] == "active"


def test_quant_lab_api_endpoints(tmp_path: Path, monkeypatch):
    _write_report(tmp_path, "range_hunter_v2_4h_usdt_btc_report.json", _sample_report())
    _write_report(tmp_path, "mm200_trend_v2_1d_usdt_btc_report.json", _sample_report("mm200_trend_v2", "1d"))
    monkeypatch.setattr(quant_lab, "project_root", lambda: tmp_path)

    client = TestClient(app)
    experiments = client.get("/api/quant-lab/experiments")
    assert experiments.status_code == 200
    ids = [item["id"] for item in experiments.json()["items"]]
    assert len(ids) == 2

    note = client.put(
        f"/api/quant-lab/experiments/{ids[0]}/annotation",
        json={"tags": ["bom em lateral"], "note": "avaliar"},
    )
    assert note.status_code == 200
    assert note.json()["annotation"]["tags"] == ["bom em lateral"]

    compare = client.post("/api/quant-lab/compare", json={"experiment_ids": ids})
    assert compare.status_code == 200
    assert len(compare.json()["metrics"]) == 2

    replay = client.get(f"/api/quant-lab/replay/{ids[0]}")
    assert replay.status_code == 200
    assert replay.json()["total_trades"] == 1

    library = client.get("/api/quant-lab/strategies")
    assert library.status_code == 200
    assert library.json()["items"]
