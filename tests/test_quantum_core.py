"""Testes do QuantumTrend Pro Core."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from atlas.core.models import Candle, IndicatorSnapshot
from atlas.quantum.alignment import AlignmentScoreEngine
from atlas.quantum.candles import bullish_rejection_candle
from atlas.quantum.decision_engine import DecisionEngine
from atlas.quantum.entry import evaluate_entry
from atlas.quantum.gates import promotion_checklist_backtest, promotion_checklist_paper
from atlas.quantum.models import EntryModule, MarketRegime, MultiTimeframeContext, RiskProfile, TimeframeSnapshot
from atlas.quantum.regime import MarketRegimeEngine


def _snap(**kwargs) -> IndicatorSnapshot:
    return IndicatorSnapshot(timestamp=datetime.now(timezone.utc), **kwargs)


def _candle(**kwargs) -> Candle:
    base = {
        "timestamp": datetime.now(timezone.utc),
        "open": 100.0,
        "high": 105.0,
        "low": 95.0,
        "close": 102.0,
        "volume": 1200.0,
    }
    base.update(kwargs)
    return Candle(**base)


def _bull_context() -> MultiTimeframeContext:
    macro = TimeframeSnapshot(
        "1d",
        _candle(close=110.0),
        _snap(ema50=105.0, ema200=95.0, adx=28.0, atr=2.0),
    )
    confirm = TimeframeSnapshot(
        "4h",
        _candle(close=108.0),
        _snap(ema20=104.0, ema50=100.0, adx=24.0),
    )
    execution = TimeframeSnapshot(
        "1h",
        _candle(open=101.0, close=103.5, low=94.0, high=104.0, volume=1500.0),
        _snap(ema20=100.0, ema200=90.0, rsi=45.0, adx=22.0, atr=1.5, volume_sma20=1000.0),
    )
    ctx = MultiTimeframeContext(execution=execution, confirm=confirm, macro=macro)
    ctx.regime = MarketRegimeEngine().classify(ctx).regime
    return ctx


def test_bullish_rejection_candle():
    candle = _candle(open=100.0, close=103.0, low=95.0, high=104.0)
    assert bullish_rejection_candle(candle, 100.0) is True


def test_regime_engine_bull():
    ctx = _bull_context()
    result = MarketRegimeEngine().classify(ctx)
    assert result.regime in {MarketRegime.BULL_TREND, MarketRegime.WEAK_BULL}


def test_pullback_entry_requires_rejection():
    ctx = _bull_context()
    result = evaluate_entry(ctx, EntryModule.PULLBACK)
    assert result is not None
    assert result.module == EntryModule.PULLBACK
    assert result.confidence > 0


def test_decision_engine_auto_selects_best_module():
    ctx = _bull_context()
    decision = DecisionEngine().evaluate(ctx, EntryModule.AUTO)
    assert decision.selected is not None
    assert decision.selected.module in {
        EntryModule.PULLBACK,
        EntryModule.BREAKOUT,
        EntryModule.SUPERTREND,
    }
    if len([r for r in decision.evaluations if r.triggered]) > 1:
        assert decision.rejected


def test_alignment_score_threshold():
    ctx = _bull_context()
    engine = AlignmentScoreEngine(risk_profile=RiskProfile.MODERATE)
    result = engine.score(ctx, entry_signal=True)
    assert 0 <= result.total <= 100
    assert result.threshold == 80


def test_promotion_gates_backtest():
    checks = promotion_checklist_backtest(
        {"profit_factor": 1.5, "win_rate": 0.55, "max_drawdown_pct": 0.12, "total_trades": 80}
    )
    assert all(item["ok"] for item in checks[:3])


def test_promotion_gates_paper():
    checks = promotion_checklist_paper(
        {"profit_factor": 1.6, "max_drawdown_pct": 0.10, "total_trades": 60}
    )
    assert all(item["ok"] for item in checks)
