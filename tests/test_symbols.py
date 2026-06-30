from __future__ import annotations

import pytest

from atlas.core.symbols import (
    OPERATED_BASES,
    build_symbol,
    compact_symbol,
    normalize_symbol,
    operated_market_watchlist,
    validate_operated_base,
)


def test_operated_bases():
    assert "BTC" in OPERATED_BASES
    assert "ETH" in OPERATED_BASES


def test_operated_market_watchlist():
    pairs = operated_market_watchlist()
    assert pairs == ["BTC/USDT", "ETH/USDT"]


def test_build_symbol_eth():
    assert build_symbol("ETH", "USDT") == "ETH/USDT"


def test_normalize_symbol_accepts_compact_and_slash():
    compact = normalize_symbol("BTCUSDT")
    slash = normalize_symbol("BTC/USDT")
    assert compact.canonical == "BTC/USDT"
    assert compact.exchange == slash.exchange == "BTC/USDT"
    assert compact.base == "BTC"
    assert compact.quote == "USDT"
    assert compact_symbol("ETH_USDT") == "ETHUSDT"


def test_report_json_basename():
    from atlas.core.symbols import report_json_basename, report_name_stem

    stem = report_name_stem("pullback_ema20_v1", "4h", "USDT", "ETH")
    assert report_json_basename(stem) == "pullback_ema20_v1_4h_usdt_eth_report.json"


def test_discover_eth_reports(tmp_path):
    from atlas.intelligence.metrics import discover_reports

    eth_plain = tmp_path / "pullback_ema20_v1_1h_usdt_eth.json"
    eth_report = tmp_path / "pullback_ema20_v1_4h_usdt_eth_report.json"
    btc_report = tmp_path / "pullback_ema20_v1_4h_usdt_report.json"
    for p in (eth_plain, eth_report, btc_report):
        p.write_text("{}", encoding="utf-8")

    names = {p.name for p in discover_reports(tmp_path)}
    assert "pullback_ema20_v1_1h_usdt_eth.json" in names
    assert "pullback_ema20_v1_4h_usdt_eth_report.json" in names
    assert "pullback_ema20_v1_4h_usdt_report.json" in names
