from __future__ import annotations

import json
from pathlib import Path

from atlas.core.config import load_config
from atlas.intelligence.analyzer import analyze_path
from atlas.intelligence.metrics import load_report
from atlas.intelligence.report import render_ai_report
from atlas.research.report_metadata import build_report_metadata, metadata_from_report_path
from atlas.strategies.metadata import parse_strategy_from_report_name, report_display_label


def test_parse_strategy_from_report_name():
    assert parse_strategy_from_report_name("range_hunter_v2_4h_report") == ("range_hunter_v2", "4h")
    assert parse_strategy_from_report_name("mm200_trend_v1_report") == ("mm200_trend_v1", None)
    assert parse_strategy_from_report_name("backtest_report") == ("unknown", None)


def test_report_display_label():
    label = report_display_label(Path("range_hunter_v2_4h_report.json"))
    assert "range_hunter_v2" in label
    assert "4h" in label
    assert "Mean Reversion" in label


def test_build_report_metadata_from_config():
    root = Path(__file__).resolve().parents[1]
    cfg_path = root / "config" / "backtest_v2.yaml"
    if not cfg_path.is_file():
        return
    config = load_config(cfg_path)
    meta = build_report_metadata(config, config_file="config/backtest_v2.yaml", report_name="x")
    assert meta["strategy"] == config.strategy.name
    assert meta["strategy_type"] == "Mean Reversion"
    assert meta["config_file"] == "config/backtest_v2.yaml"
    assert meta["market"]
    assert meta["timeframe"]


def test_legacy_report_metadata_inference():
    root = Path(__file__).resolve().parents[1]
    report = root / "data" / "reports" / "mm200_trend_v1_report.json"
    if not report.is_file():
        return
    raw = json.loads(report.read_text(encoding="utf-8"))
    meta = metadata_from_report_path(report, raw)
    assert meta["strategy"] == "mm200_trend_v1"
    assert meta["strategy_type"] == "Trend Following"
    assert meta.get("legacy_report") is True


def test_ai_report_includes_strategy_metadata():
    root = Path(__file__).resolve().parents[1]
    report = root / "data" / "reports" / "mm200_trend_v1_report.json"
    if not report.is_file():
        return
    analysis = analyze_path(report)
    md = render_ai_report(analysis)
    assert "**Strategy:** mm200_trend_v1" in md
    assert "**Strategy Type:** Trend Following" in md
    assert "Identificacao do teste" in md
    assert analysis.metadata["strategy"] == "mm200_trend_v1"


def test_load_report_uses_metadata_strategy():
    root = Path(__file__).resolve().parents[1]
    report = root / "data" / "reports" / "mm200_trend_v1_report.json"
    if not report.is_file():
        return
    bundle = load_report(report)
    assert bundle.strategy == "mm200_trend_v1"
    assert bundle.metadata.get("strategy_type") == "Trend Following"
    assert bundle.metadata.get("source_path")
