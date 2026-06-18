"""Testes de serviços QuantumTrend."""
from __future__ import annotations

from atlas.quantum.gates import promotion_checklist_backtest, promotion_checklist_paper
from atlas.services.quantum_service import compute_drawdown_curve
from atlas.strategies.metadata import is_legacy_strategy, list_primary_strategies


def test_primary_strategies():
    assert "quantum_trend_pro" in list_primary_strategies()


def test_legacy_flag():
    assert is_legacy_strategy("mm200_trend_v2") is True
    assert is_legacy_strategy("quantum_trend_pro") is False


def test_drawdown_curve():
    curve = compute_drawdown_curve([
        {"day": "D1", "equity": 100},
        {"day": "D2", "equity": 90},
        {"day": "D3", "equity": 95},
    ])
    assert curve[1]["drawdown_pct"] == 10.0


def test_gates_stages():
    backtest = promotion_checklist_backtest({"profit_factor": 1.5, "win_rate": 0.55, "max_drawdown_pct": 0.15, "total_trades": 10})
    paper = promotion_checklist_paper({"profit_factor": 1.6, "max_drawdown_pct": 0.12, "total_trades": 55})
    assert all(item["stage"] == "backtest" for item in backtest)
    assert all(item["stage"] == "paper" for item in paper)
