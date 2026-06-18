from __future__ import annotations

from atlas.services.analytics import load_trades_for_results, trade_from_report_row
from atlas.services.terminal import get_results_payload


def test_trade_from_report_row_maps_engine_fields():
    trade = trade_from_report_row(
        {
            "entry_time": "2026-03-04T12:00:00+00:00",
            "exit_time": "2026-03-06T12:00:00+00:00",
            "entry_price": 71146.95,
            "exit_price": 68470.45,
            "pnl": -98.04,
            "pnl_pct": -0.039581672056629894,
        }
    )
    assert trade.entry == 71146.95
    assert trade.exit == 68470.45
    assert round(trade.pnl_pct, 2) == -3.96


def test_get_results_payload_with_saved_reports():
    from atlas.services.terminal import get_results_payload

    payload = get_results_payload()
    assert payload["metrics"]["trades"] >= 0
    assert isinstance(payload["equity_curve"], list)
    assert payload["equity_curve"]
    assert "day" in payload["equity_curve"][0]
    assert "equity" in payload["equity_curve"][0]
    assert payload["strategy"]

    specific = get_results_payload(strategy="range_hunter_v1", timeframe="4h")
    assert specific["strategy"] == "range_hunter_v1"
    assert specific["timeframe"] == "4h"


def test_load_trades_for_results_does_not_crash():
    metrics, trades, equity = load_trades_for_results()
    assert "trades" in metrics
    assert isinstance(trades, list)
    assert isinstance(equity, list)
