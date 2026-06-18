"""Restaura módulos Python do ATLAS completo a partir do GitHub (branch main)."""
from __future__ import annotations

import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/rafaelcostr/Quantum-Trend/main"
ROOT = Path(__file__).resolve().parents[1]

PATHS = [
    # strategies
    "src/atlas/strategies/__init__.py",
    "src/atlas/strategies/metadata.py",
    "src/atlas/strategies/bb_squeeze_v1.py",
    "src/atlas/strategies/range_hunter_v1.py",
    "src/atlas/strategies/range_hunter_v2.py",
    "src/atlas/strategies/mm200_trend_v1.py",
    "src/atlas/strategies/mm200_trend_v2.py",
    "src/atlas/strategies/mm200_daily_macro_v1.py",
    "src/atlas/strategies/portfolio_v1.py",
    "src/atlas/strategies/regime_switching_v1.py",
    "src/atlas/strategies/registry.py",
    # core
    "src/atlas/core/models.py",
    "src/atlas/core/config.py",
    "src/atlas/core/risk.py",
    "src/atlas/core/indicators.py",
    "src/atlas/brokers/binance.py",
    # runtime
    "src/atlas/runtime/__init__.py",
    "src/atlas/runtime/engine.py",
    "src/atlas/runtime/reconciler.py",
    "src/atlas/runtime/journal.py",
    "src/atlas/runtime/paper_worker.py",
    "src/atlas/runtime/runner.py",
    "src/atlas/monitoring/watchdog.py",
    # research
    "src/atlas/research/backtester.py",
    "src/atlas/research/statistics.py",
    "src/atlas/research/report_metadata.py",
    "src/atlas/research/walk_forward.py",
    # intelligence
    "src/atlas/intelligence/__init__.py",
    "src/atlas/intelligence/score.py",
    "src/atlas/intelligence/metrics.py",
    "src/atlas/intelligence/analyzer.py",
    "src/atlas/intelligence/compare_report.py",
    "src/atlas/intelligence/confidence.py",
    "src/atlas/intelligence/diagnostics.py",
    "src/atlas/intelligence/report.py",
    "src/atlas/intelligence/monte_carlo.py",
    "src/atlas/intelligence/models.py",
    "src/atlas/intelligence/research_store.py",
    "src/atlas/intelligence/level2_metrics.py",
    "src/atlas/intelligence/level2_diagnostics.py",
    "src/atlas/intelligence/level3_metrics.py",
    "src/atlas/intelligence/level3_diagnostics.py",
    # configs
    "config/backtest.yaml",
    "config/backtest_v2.yaml",
    "config/backtest_v2_1.yaml",
    "config/backtest_v2_2.yaml",
    "config/backtest_v3.yaml",
    "config/backtest_portfolio.yaml",
    "config/backtest_daily_macro.yaml",
    "config/live.yaml",
    "config/paper.yaml",
    # tests
    "tests/test_engine.py",
    "tests/test_range_hunter.py",
    "tests/test_reconciler.py",
    "tests/test_watchdog.py",
    "tests/test_backtester.py",
    "tests/test_intelligence.py",
]


def main() -> None:
    ok, fail = 0, 0
    for rel in PATHS:
        dest = ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f"{BASE}/{rel}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                dest.write_bytes(resp.read())
            print(f"OK  {rel}")
            ok += 1
        except Exception as exc:
            print(f"FAIL {rel}: {exc}")
            fail += 1
    print(f"\nConcluído: {ok} ok, {fail} falhas")


if __name__ == "__main__":
    main()
