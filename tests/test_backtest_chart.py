"""Testes — gráfico de backtest com trades."""
from __future__ import annotations

from atlas.services.backtest_chart import get_backtest_chart_payload


def test_backtest_chart_missing_report():
    payload = get_backtest_chart_payload(
        strategy="nonexistent_strategy_xyz",
        timeframe="4h",
        base="BTC",
    )
    assert payload["bars"] == []
    assert payload["markers"] == []
    assert payload.get("error")
