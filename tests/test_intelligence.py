from __future__ import annotations

from pathlib import Path

from atlas.intelligence.analyzer import analyze_path
from atlas.intelligence.report import render_ai_report
from atlas.intelligence.score import compute_atlas_score, score_label


def test_analyze_mm200_report():
    root = Path(__file__).resolve().parents[1]
    report = root / "data" / "reports" / "mm200_trend_v1_report.json"
    if not report.is_file():
        return
    analysis = analyze_path(report)
    assert analysis.strategy == "mm200_trend_v1"
    assert analysis.level1.atlas_score > 0
    assert analysis.level1.total_trades if hasattr(analysis.level1, "total_trades") else True
    assert len(analysis.level1.strengths) >= 1
    assert analysis.raw["total_trades"] == 84


def test_analyze_mm200_report_fields():
    root = Path(__file__).resolve().parents[1]
    report = root / "data" / "reports" / "mm200_trend_v1_report.json"
    if not report.is_file():
        return
    analysis = analyze_path(report)
    assert analysis.raw["profit_factor"] > 1.0
    assert analysis.level1.confidence in {"Alta Confiança", "Média Confiança", "Baixa Confiança"}


def test_score_label():
    assert score_label(92)[0] == "Excelente"
    assert score_label(55)[0] == "Rejeitado"


def test_compute_atlas_score_caps_low_trades():
    score = compute_atlas_score(
        max_drawdown_pct=0.10,
        profit_factor=2.0,
        expectancy_pct=0.02,
        sharpe=1.5,
        net_profit_pct=1.0,
        total_trades=10,
        confidence_subscore=80,
    )
    assert score <= 65


def test_ai_report_markdown():
    root = Path(__file__).resolve().parents[1]
    report = root / "data" / "reports" / "mm200_trend_v1_report.json"
    if not report.is_file():
        return
    analysis = analyze_path(report)
    md = render_ai_report(analysis)
    assert "# ATLAS QUANT REPORT" in md
    assert "Identificacao do teste" in md
    assert "**Strategy Type:**" in md
    assert "NÍVEL 1" in md
    assert analysis.strategy in md
