from __future__ import annotations

from pathlib import Path

from atlas.intelligence.compare_report import (
    UNIFIED_AI_REPORT_NAME,
    build_comparison_report,
    export_all_reports,
    render_unified_ai_report,
)


def test_build_comparison_report_empty(tmp_path: Path):
    res = build_comparison_report(tmp_path / "reports")
    assert res["ok"] is False


def test_build_comparison_report_with_file(tmp_path: Path):
    reports = tmp_path / "reports"
    reports.mkdir()
    sample = {
        "metadata": {
            "strategy": "range_hunter_v2",
            "strategy_version": "2.0.0",
            "strategy_type": "Mean Reversion",
            "market": "BTC/USDT",
            "timeframe": "4h",
            "config_file": "config/backtest_v2.yaml",
            "mode": "backtest",
            "risk_model": "risk_based",
            "position_size": "1% per trade",
            "fee_rate": 0.001,
            "slippage_rate": 0.0005,
            "initial_capital": 10000,
        },
        "statistics": {
            "net_profit": 500.0,
            "net_profit_pct": 0.05,
            "total_trades": 40,
            "win_rate": 0.55,
            "profit_factor": 1.4,
            "max_drawdown_pct": 0.12,
            "best_trade_pct": 0.03,
            "worst_trade_pct": -0.02,
            "avg_trade_pct": 0.001,
            "sharpe_ratio": 1.1,
        },
        "trades": [
            {
                "entry_time": "2024-01-01T00:00:00+00:00",
                "exit_time": "2024-01-02T00:00:00+00:00",
                "entry_price": 40000,
                "exit_price": 41000,
                "pnl": 100,
                "pnl_pct": 0.025,
                "fees": 1,
                "strategy": "range_hunter_v2",
                "metadata": {},
            }
        ]
        * 40,
        "equity_curve": [
            {"timestamp": "2024-01-01T00:00:00+00:00", "equity": 10000},
            {"timestamp": "2024-06-01T00:00:00+00:00", "equity": 10500},
        ],
    }
    (reports / "range_hunter_v2_4h_usdt_report.json").write_text(
        __import__("json").dumps(sample),
        encoding="utf-8",
    )
    res = build_comparison_report(reports, include_full=False)
    assert res["ok"] is True
    assert res["count"] == 1
    md = res["markdown"]
    assert "# ATLAS QUANT — RELATÓRIO COMPARATIVO" in md
    assert "range_hunter_v2" in md
    assert "Ranking por Atlas Score" in md

    full = build_comparison_report(reports, include_full=True)
    assert "# ATLAS QUANT REPORT" in full["markdown"]
    assert "RELATÓRIOS INDIVIDUAIS COMPLETOS" in full["markdown"]


def test_export_all_reports_creates_zip(tmp_path: Path):
    reports = tmp_path / "reports"
    reports.mkdir()
    sample = {
        "metadata": {
            "strategy": "range_hunter_v2",
            "strategy_version": "2.0.0",
            "strategy_type": "Mean Reversion",
            "market": "BTC/USDT",
            "timeframe": "4h",
            "config_file": "config/backtest_v2.yaml",
            "mode": "backtest",
            "risk_model": "risk_based",
            "position_size": "1% per trade",
            "fee_rate": 0.001,
            "slippage_rate": 0.0005,
            "initial_capital": 10000,
        },
        "statistics": {
            "net_profit": 500.0,
            "net_profit_pct": 0.05,
            "total_trades": 40,
            "win_rate": 0.55,
            "profit_factor": 1.4,
            "max_drawdown_pct": 0.12,
            "best_trade_pct": 0.03,
            "worst_trade_pct": -0.02,
            "avg_trade_pct": 0.001,
            "sharpe_ratio": 1.1,
        },
        "trades": [
            {
                "entry_time": "2024-01-01T00:00:00+00:00",
                "exit_time": "2024-01-02T00:00:00+00:00",
                "entry_price": 40000,
                "exit_price": 41000,
                "pnl": 100,
                "pnl_pct": 0.025,
                "fees": 1,
                "strategy": "range_hunter_v2",
                "metadata": {},
            }
        ]
        * 40,
        "equity_curve": [
            {"timestamp": "2024-01-01T00:00:00+00:00", "equity": 10000},
            {"timestamp": "2024-06-01T00:00:00+00:00", "equity": 10500},
        ],
    }
    (reports / "range_hunter_v2_4h_usdt_report.json").write_text(
        __import__("json").dumps(sample),
        encoding="utf-8",
    )
    res = export_all_reports(reports)
    assert res["ok"] is True
    assert res["individual_count"] == 1
    assert len(res["individual_files"]) == 1
    assert Path(res["zip_path"]).is_file()
    assert Path(res["unified_path"]).is_file()
    unified = Path(res["unified_path"]).read_text(encoding="utf-8")
    assert "RELATÓRIO ÚNICO" in unified
    assert "Como usar com IA" in unified
    assert UNIFIED_AI_REPORT_NAME.endswith(".md")


def test_render_unified_ai_report(tmp_path: Path):
    reports = tmp_path / "reports"
    reports.mkdir()
    sample = {
        "metadata": {
            "strategy": "range_hunter_v2",
            "strategy_version": "2.0.0",
            "strategy_type": "Mean Reversion",
            "market": "BTC/USDT",
            "timeframe": "4h",
            "config_file": "config/backtest_v2.yaml",
            "mode": "backtest",
            "risk_model": "risk_based",
            "position_size": "1% per trade",
            "fee_rate": 0.001,
            "slippage_rate": 0.0005,
            "initial_capital": 10000,
        },
        "statistics": {
            "net_profit": 500.0,
            "net_profit_pct": 0.05,
            "total_trades": 40,
            "win_rate": 0.55,
            "profit_factor": 1.4,
            "max_drawdown_pct": 0.12,
            "best_trade_pct": 0.03,
            "worst_trade_pct": -0.02,
            "avg_trade_pct": 0.001,
            "sharpe_ratio": 1.1,
        },
        "trades": [
            {
                "entry_time": "2024-01-01T00:00:00+00:00",
                "exit_time": "2024-01-02T00:00:00+00:00",
                "entry_price": 40000,
                "exit_price": 41000,
                "pnl": 100,
                "pnl_pct": 0.025,
                "fees": 1,
                "strategy": "range_hunter_v2",
                "metadata": {},
            }
        ]
        * 40,
        "equity_curve": [
            {"timestamp": "2024-01-01T00:00:00+00:00", "equity": 10000},
            {"timestamp": "2024-06-01T00:00:00+00:00", "equity": 10500},
        ],
    }
    (reports / "range_hunter_v2_4h_usdt_report.json").write_text(
        __import__("json").dumps(sample),
        encoding="utf-8",
    )
    from atlas.intelligence.compare_report import analyze_all_reports

    analyses, errors = analyze_all_reports(reports)
    md = render_unified_ai_report(analyses, errors)
    assert "RELATÓRIO COMPARATIVO" in md
    assert "# ATLAS QUANT REPORT" in md
    assert "range_hunter_v2" in md
