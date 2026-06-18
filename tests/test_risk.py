from datetime import datetime, timezone

import pytest

from atlas.core.models import PortfolioState, RiskConfig, Signal, SignalAction
from atlas.core.risk import RiskManager


def test_risk_blocks_when_kill_switch():
    rm = RiskManager(RiskConfig())
    rm.activate_kill_switch()
    decision = rm.approve_entry(
        Signal(action=SignalAction.ENTER_LONG, stop_price=90.0),
        PortfolioState(cash=10_000, equity=10_000),
        datetime.now(timezone.utc),
        100.0,
    )
    assert not decision.approved


def test_risk_position_size():
    rm = RiskManager(RiskConfig(risk_per_trade=0.01))
    qty = rm.position_size(equity=10_000, entry_price=100, stop_price=95)
    assert qty == pytest.approx(20.0, rel=0.01)


def test_apply_risk_to_engine(monkeypatch, tmp_path):
    from atlas.runtime.risk_store import apply_risk_to_engine, update_risk_settings

    path = tmp_path / "risk.json"
    monkeypatch.setattr("atlas.runtime.risk_store._PATH", path)
    monkeypatch.setattr("atlas.runtime.risk_store._store", None)

    class _FakeEngine:
        def __init__(self) -> None:
            self.risk = RiskManager(RiskConfig(risk_per_trade=0.005, max_daily_drawdown=0.03))

    update_risk_settings(risk_per_trade_pct=2.0, daily_stop_pct=4.0)
    engine = _FakeEngine()
    apply_risk_to_engine(engine)

    assert engine.risk.config.risk_per_trade == 0.02
    assert engine.risk.config.max_daily_drawdown == 0.04
