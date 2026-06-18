from __future__ import annotations

from pathlib import Path

import numpy as np

from atlas.intelligence.analyzer import analyze_path
from atlas.intelligence.level3_metrics import (
    build_level3_values,
    compute_kelly,
    compute_skewness_kurtosis,
    compute_ulcer_index,
)
from atlas.intelligence.metrics import load_report
from atlas.intelligence.monte_carlo import monte_carlo_bootstrap
from atlas.intelligence.report import render_ai_report


def _sample_trades(n: int = 30) -> list[dict]:
    rng = np.random.default_rng(42)
    return [
        {
            "pnl": float(rng.choice([120, -60, 80, -40])),
            "pnl_pct": float(rng.uniform(-0.02, 0.04)),
            "entry_time": f"2024-01-{i % 28 + 1:02d}T00:00:00+00:00",
            "exit_time": f"2024-01-{i % 28 + 2:02d}T00:00:00+00:00",
        }
        for i in range(n)
    ]


def test_monte_carlo_bootstrap():
    trades = _sample_trades(40)
    mc = monte_carlo_bootstrap(trades, 10000.0, n_simulations=200, seed=1)
    assert mc is not None
    assert "mc_return_median" in mc
    assert mc["mc_return_worst"] <= mc["mc_return_median"] <= mc["mc_return_best"]


def test_kelly_and_ulcer():
    kelly = compute_kelly(0.4, 2.0)
    assert kelly is not None
    assert 0 <= kelly <= 1

    equity = [{"timestamp": f"2024-01-{i:02d}", "equity": 10000 + i * 50 - (i % 5) * 200} for i in range(1, 40)]
    ulcer = compute_ulcer_index(equity)
    assert ulcer is not None
    assert ulcer >= 0


def test_skewness_kurtosis():
    trades = [{"pnl_pct": x} for x in [0.01, 0.02, -0.01, 0.03, -0.02] * 5]
    skew, kurt = compute_skewness_kurtosis(trades)
    assert skew is not None
    assert kurt is not None


def test_level3_on_mm200_report():
    root = Path(__file__).resolve().parents[1]
    report = root / "data" / "reports" / "mm200_trend_v1_report.json"
    if not report.is_file():
        return
    analysis = analyze_path(report)
    assert analysis.level3 is not None
    assert analysis.level3.diagnosis
    assert analysis.raw.get("mc_return_median") is not None
    assert analysis.raw.get("ulcer_index") is not None


def test_level3_with_walkforward():
    root = Path(__file__).resolve().parents[1]
    report = root / "data" / "reports" / "mm200_trend_v1_report.json"
    wf = root / "data" / "reports" / "mm200_trend_v1_walkforward.json"
    if not report.is_file() or not wf.is_file():
        return
    analysis = analyze_path(report)
    assert analysis.level3 is not None
    assert analysis.level3.has_walkforward
    assert analysis.raw.get("oos_return") is not None
    promo = analysis.level1.promotion_backtest_paper
    wf_item = next(c for c in promo if "Walk-forward" in c["label"])
    assert wf_item["value"] != "Pendente"


def test_build_level3_values_walkforward():
    root = Path(__file__).resolve().parents[1]
    report = root / "data" / "reports" / "mm200_trend_v1_report.json"
    if not report.is_file():
        return
    bundle = load_report(report)
    wf = {
        "out_of_sample": {"net_profit_pct": 0.12, "sharpe_ratio": 1.1, "profit_factor": 1.4},
        "in_sample": {"net_profit_pct": 0.80},
        "oos_trades": 20,
        "walk_forward_efficiency": 0.15,
        "split_timestamp": "2025-01-01",
    }
    vals = build_level3_values(bundle, wf, payoff_ratio=2.0, win_rate=0.35)
    assert vals["oos_return"] == 0.12
    assert vals["walk_forward_efficiency"] == 0.15


def test_ai_report_includes_level3():
    root = Path(__file__).resolve().parents[1]
    report = root / "data" / "reports" / "mm200_trend_v1_report.json"
    if not report.is_file():
        return
    analysis = analyze_path(report)
    md = render_ai_report(analysis)
    assert "NÍVEL 3" in md
    assert "Monte Carlo" in md
    assert analysis.level3 is not None
    assert analysis.level3.diagnosis in md
