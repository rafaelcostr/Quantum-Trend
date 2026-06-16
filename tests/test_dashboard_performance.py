from __future__ import annotations

from datetime import datetime, timezone

from atlas.dashboard.performance import compute_performance, extract_trade_markers


def test_extract_trade_markers():
    events = [
        {
            "ts": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "event": "entry",
            "payload": {"fill": {"filled_price": 42000.0}, "signal": "bullish cross"},
        },
        {
            "ts": datetime(2024, 1, 2, tzinfo=timezone.utc),
            "event": "exit",
            "payload": {"fill": {"filled_price": 43000.0}, "signal": "bearish cross"},
        },
    ]
    markers = extract_trade_markers(events)
    assert len(markers) == 2
    assert markers[0].side == "buy"
    assert markers[1].side == "sell"


def test_compute_performance():
    events = [
        {"ts": "2024-01-01T00:00:00+00:00", "event": "tick", "payload": {"equity": 5000}},
        {"ts": "2024-01-02T00:00:00+00:00", "event": "tick", "payload": {"equity": 5200}},
        {"ts": "2024-01-03T00:00:00+00:00", "event": "tick", "payload": {"equity": 4800}},
        {"ts": "2024-01-04T00:00:00+00:00", "event": "entry", "payload": {"fill": {"filled_price": 40000}}},
    ]
    perf = compute_performance(events, initial_capital=5000, current_equity=5100)
    assert perf.net_pnl == 100
    assert perf.trade_count == 1
    assert perf.max_drawdown_pct > 0
    assert len(perf.equity_curve) >= 3
