from __future__ import annotations

from atlas.core.models import ExchangeConfig, StrategyConfig
from atlas.runtime.operational_safety import (
    assert_no_conflicting_configs,
    begin_order_decision,
    evaluate_scoped_kill_switch,
    finish_order_decision,
    set_scoped_kill_switch,
)


class Cfg:
    def __init__(self, symbol: str, timeframe: str, strategy: str) -> None:
        self.exchange = ExchangeConfig(symbol=symbol, timeframe=timeframe)
        self.strategy = StrategyConfig(name=strategy)


def test_conflicting_configs_block_same_symbol_timeframe_strategy():
    configs = [
        ("slot_a", Cfg("BTC/USDT", "4h", "pullback_ema20_v1")),
        ("slot_b", Cfg("BTC/USDT", "4h", "pullback_ema20_v1")),
    ]

    try:
        assert_no_conflicting_configs(configs)
    except RuntimeError as exc:
        assert "Bot conflitante" in str(exc)
    else:
        raise AssertionError("conflito deveria ser bloqueado")


def test_order_decision_idempotency_blocks_pending_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr("atlas.runtime.operational_safety._PATH", tmp_path / "ops.json")
    accepted, previous = begin_order_decision("decision-1", context={"symbol": "BTC/USDT"})
    duplicate, duplicate_previous = begin_order_decision("decision-1", context={"symbol": "BTC/USDT"})

    assert accepted is True
    assert previous is None
    assert duplicate is False
    assert duplicate_previous is not None

    finish_order_decision("decision-1", status="failed", result={"message": "network"})
    retry, _ = begin_order_decision("decision-1", context={"symbol": "BTC/USDT"})
    assert retry is True


def test_scoped_kill_switch_blocks_asset_and_strategy(tmp_path, monkeypatch):
    monkeypatch.setattr("atlas.runtime.operational_safety._PATH", tmp_path / "ops.json")
    set_scoped_kill_switch(scope="asset", key="BTC", active=True, reason="manutenção")

    asset = evaluate_scoped_kill_switch(
        global_active=False,
        symbol="BTC/USDT",
        strategy="pullback_ema20_v1",
    )
    other = evaluate_scoped_kill_switch(
        global_active=False,
        symbol="ETH/USDT",
        strategy="pullback_ema20_v1",
    )

    assert asset.blocked is True
    assert "manutenção" in (asset.reason or "")
    assert other.blocked is False

    set_scoped_kill_switch(scope="strategy", key="pullback_ema20_v1", active=True, reason="bug")
    strategy = evaluate_scoped_kill_switch(
        global_active=False,
        symbol="ETH/USDT",
        strategy="pullback_ema20_v1",
    )
    assert strategy.blocked is True
    assert "bug" in (strategy.reason or "")
