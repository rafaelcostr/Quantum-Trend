from __future__ import annotations

from fastapi.testclient import TestClient

from atlas.api.main import create_app
from atlas.monitoring.incident_manager import incidents_payload, open_incident, resolve_incident


def test_incident_lifecycle(monkeypatch, tmp_path):
    path = tmp_path / "incidents.json"
    monkeypatch.setattr("atlas.monitoring.incident_manager._PATH", path)

    item = open_incident(
        type="order_rejected",
        message="Ordem rejeitada",
        module="runtime.engine",
        strategy="pullback_ema20_v1",
        notify=False,
    )
    assert item["status"] == "open"
    assert incidents_payload()["open"] == 1

    resolved = resolve_incident(item["id"], message="ok", notify=False)
    assert resolved is not None
    assert resolved["status"] == "resolved"
    assert incidents_payload()["resolved"] == 1


def test_monitoring_health_endpoint(monkeypatch, tmp_path):
    monkeypatch.setattr("atlas.monitoring.incident_manager._PATH", tmp_path / "incidents.json")
    client = TestClient(create_app())
    res = client.get("/api/monitoring/health")
    assert res.status_code == 200
    body = res.json()
    assert body["api"]["online"] is True
    assert "binance" in body
    assert "incidents" in body


def test_monitoring_incident_resolve_endpoint(monkeypatch, tmp_path):
    monkeypatch.setattr("atlas.monitoring.incident_manager._PATH", tmp_path / "incidents.json")
    item = open_incident(type="api_timeout", message="API sem resposta", module="api", notify=False)
    client = TestClient(create_app())
    res = client.post(f"/api/monitoring/incidents/{item['id']}/resolve")
    assert res.status_code == 200
    assert res.json()["incident"]["status"] == "resolved"
