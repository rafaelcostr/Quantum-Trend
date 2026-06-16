from __future__ import annotations

from pathlib import Path

from atlas.intelligence.analyzer import analyze_path
from atlas.intelligence.level2_metrics import (
    compute_payoff_ratio,
    compute_streaks,
    compute_recovery_factor,
)


def test_level2_metrics_on_mm200():
    root = Path(__file__).resolve().parents[1]
    report = root / "data" / "reports" / "mm200_trend_v1_report.json"
    if not report.is_file():
        return
    analysis = analyze_path(report)
    assert analysis.level2 is not None
    assert len(analysis.level2.metrics) == 7
    assert analysis.level2.diagnosis
    assert analysis.raw.get("sortino_ratio") is not None
    assert analysis.raw.get("recovery_factor") is not None


def test_payoff_and_streaks():
    trades = [
        {"pnl": 100, "entry_time": "2024-01-01T00:00:00+00:00", "exit_time": "2024-01-02T00:00:00+00:00"},
        {"pnl": -50, "entry_time": "2024-01-03T00:00:00+00:00", "exit_time": "2024-01-04T00:00:00+00:00"},
        {"pnl": -30, "entry_time": "2024-01-05T00:00:00+00:00", "exit_time": "2024-01-06T00:00:00+00:00"},
        {"pnl": 200, "entry_time": "2024-01-07T00:00:00+00:00", "exit_time": "2024-01-08T00:00:00+00:00"},
    ]
    payoff = compute_payoff_ratio(trades)
    assert payoff == 3.75
    win, loss = compute_streaks(trades)
    assert win == 1
    assert loss == 2


def test_recovery_factor():
    rf = compute_recovery_factor(net_profit=5000, max_dd_pct=0.25, initial_capital=10000)
    assert rf == 2.0


def test_ai_report_includes_level2():
    root = Path(__file__).resolve().parents[1]
    report = root / "data" / "reports" / "mm200_trend_v1_report.json"
    if not report.is_file():
        return
    from atlas.intelligence.report import render_ai_report

    analysis = analyze_path(report)
    md = render_ai_report(analysis)
    assert "NÍVEL 2" in md
    assert "Sortino" in md
    assert analysis.level2 is not None
    assert analysis.level2.diagnosis in md
