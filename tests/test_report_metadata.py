from __future__ import annotations

import json
from pathlib import Path

from atlas.core.config import load_config
from atlas.core.symbols import parse_strategy_from_report_name
from atlas.intelligence.analyzer import analyze_path
from atlas.intelligence.metrics import load_report
from atlas.intelligence.report import render_ai_report
from atlas.research.report_metadata import build_report_metadata, metadata_from_report_path
from atlas.strategies.metadata import report_display_label


def test_period_from_report_raw():
    from atlas.research.report_metadata import period_from_report_raw

    raw = {
        "equity_curve": [
            {"timestamp": "2017-08-17T00:00:00+00:00", "equity": 10000},
            {"timestamp": "2024-06-01T00:00:00+00:00", "equity": 15000},
        ]
    }
    period = period_from_report_raw(raw)
    assert period["period_start"] == "2017-08-17"
    assert period["period_end"] == "2024-06-01"
    assert period["period_days"] is not None
    assert period["period_days"] > 2400


def test_parse_strategy_from_report_name():
    assert parse_strategy_from_report_name("range_hunter_v2_4h_usdt_report") == (
        "range_hunter_v2",
        "4h",
        "USDT",
        None,
    )
    assert parse_strategy_from_report_name("pullback_ema20_v1_4h_usdt_eth_report") == (
        "pullback_ema20_v1",
        "4h",
        "USDT",
        "ETH",
    )
    assert parse_strategy_from_report_name("range_hunter_v2_4h_report") == ("range_hunter_v2", "4h", None, None)
    assert parse_strategy_from_report_name("mm200_trend_v1_report") == ("mm200_trend_v1", None, None, None)
    assert parse_strategy_from_report_name("backtest_report") == ("unknown", None, None, None)


def test_report_display_label():
    label = report_display_label(Path("range_hunter_v2_4h_report.json"))
    assert "range_hunter_v2" in label
    assert "4h" in label
    assert "Mean Reversion" in label


def test_report_display_label_legacy():
    label = report_display_label(Path("backtest_report.json"))
    assert "antigo" in label or "backtest" in label


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


def test_remove_stale_reports_replaces_same_strategy_timeframe(tmp_path: Path):
    from atlas.research.report_metadata import remove_stale_reports

    old = tmp_path / "range_hunter_v2_4h_usdt_report.json"
    legacy = tmp_path / "range_hunter_v2_4h_report.json"
    other_quote = tmp_path / "range_hunter_v2_4h_usdc_report.json"
    other_tf = tmp_path / "range_hunter_v2_1d_usdt_report.json"
    other_strategy = tmp_path / "mm200_trend_v1_4h_usdt_report.json"
    for p in (old, legacy, other_quote, other_tf, other_strategy):
        p.write_text("{}", encoding="utf-8")

    removed = remove_stale_reports(
        tmp_path,
        strategy="range_hunter_v2",
        timeframe="4h",
        quote="USDT",
        base="BTC",
    )

    assert "range_hunter_v2_4h_usdt_report.json" in removed
    assert "range_hunter_v2_4h_report.json" in removed
    assert other_quote.is_file()
    assert other_tf.is_file()
    assert other_strategy.is_file()
    assert not old.is_file()
    assert not legacy.is_file()


def test_remove_stale_reports_keeps_other_base(tmp_path: Path):
    from atlas.research.report_metadata import remove_stale_reports

    btc = tmp_path / "range_hunter_v2_4h_usdt_btc_report.json"
    eth = tmp_path / "range_hunter_v2_4h_usdt_eth_report.json"
    btc.write_text("{}", encoding="utf-8")
    eth.write_text("{}", encoding="utf-8")

    removed = remove_stale_reports(
        tmp_path,
        strategy="range_hunter_v2",
        timeframe="4h",
        quote="USDT",
        base="BTC",
    )

    assert btc.name in removed
    assert eth.is_file()
