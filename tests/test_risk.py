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


def test_risk_position_size_scales_with_drawdown_and_volatility():
    rm = RiskManager(
        RiskConfig(
            risk_per_trade=0.02,
            target_volatility_pct=0.10,
            max_drawdown_pct=0.20,
        )
    )
    base = rm.position_size(10_000, 100, 95, metadata={"volatility_pct": 0.10})
    rm.update_peak(10_000)
    scaled = rm.position_size(9_000, 100, 95, metadata={"volatility_pct": 0.20})
    assert scaled < base


def test_portfolio_risk_scales_correlated_exposure(monkeypatch):
    from atlas.core.models import Position, Side
    from atlas.runtime.portfolio_risk import evaluate_entry_risk

    class _Engine:
        def __init__(self) -> None:
            self.config = type(
                "Cfg",
                (),
                {
                    "exchange": type("Exchange", (), {"symbol": "BTC/USDT", "timeframe": "4h"})(),
                    "strategy": type("Strategy", (), {"name": "pullback_ema20_v1"})(),
                },
            )()
            self._position = Position(
                symbol="BTC/USDT",
                side=Side.BUY,
                quantity=6,
                entry_price=1000,
                entry_time=datetime.now(timezone.utc),
                strategy="pullback_ema20_v1",
            )

    class _Pool:
        def engines(self):
            return [("slot-a", _Engine())]

    monkeypatch.setattr("atlas.runtime.bot_runner.bot_pool", _Pool())
    decision = evaluate_entry_risk(
        config=RiskConfig(
            max_exposure_pct=0.95,
            max_exposure_per_timeframe_pct=0.90,
            max_exposure_per_direction_pct=0.90,
            correlation_threshold=0.50,
            correlation_risk_scale=0.5,
        ),
        equity=10_000,
        symbol="ETH/USDT",
        strategy="breakout_high20_v1",
        timeframe="4h",
        side="long",
        proposed_notional=1_000,
    )
    assert decision.approved
    assert decision.scale == pytest.approx(0.5)
