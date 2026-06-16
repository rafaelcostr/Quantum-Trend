from datetime import datetime, timezone

import pytest

from atlas.core.config import RiskConfig
from atlas.core.models import PortfolioState, Signal, SignalAction
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
