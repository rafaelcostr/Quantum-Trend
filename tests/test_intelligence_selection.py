"""Testes — recomendações IA de Seleção."""
from __future__ import annotations

from atlas.services.intelligence_selection import build_selection_payload


def test_build_selection_payload_structure():
    matrix = {
        "items": [
            {
                "ok": True,
                "strategy": "pullback_ema20_v1",
                "strategy_label": "Pullback EMA20",
                "timeframe": "4h",
                "market_type": "bull",
                "base_asset": "BTC",
                "metrics": {"atlas_score": 72, "profit_factor": 1.8, "win_rate_pct": 55, "max_drawdown_pct": 12},
            },
            {
                "ok": True,
                "strategy": "range_hunter_v1",
                "strategy_label": "Range Hunter",
                "timeframe": "4h",
                "market_type": "range",
                "base_asset": "BTC",
                "metrics": {"atlas_score": 65, "profit_factor": 1.4, "win_rate_pct": 52, "max_drawdown_pct": 8},
            },
            {
                "ok": True,
                "strategy": "pullback_short_v1",
                "strategy_label": "Pullback Short",
                "timeframe": "4h",
                "market_type": "bear",
                "base_asset": "ETH",
                "metrics": {"atlas_score": 68, "profit_factor": 1.6, "win_rate_pct": 50, "max_drawdown_pct": 10},
            },
        ],
        "by_asset": {},
    }
    payload = build_selection_payload(matrix)
    assert payload["slots_per_asset"] == 6
    assert len(payload["assets"]) == 2

    btc = next(a for a in payload["assets"] if a["base"] == "BTC")
    bull_pack = btc["packs"]["bull_range"]
    bear_pack = btc["packs"]["bear_range"]

    assert bull_pack["label"] == "Alta + Lateral"
    assert bear_pack["label"] == "Baixa + Lateral"
    assert len(bull_pack["slots"]) == 6
    assert len(bear_pack["slots"]) == 6

    trend_types = {s["market_type"] for s in bull_pack["slots"][:3]}
    range_types = {s["market_type"] for s in bull_pack["slots"][3:6]}
    assert trend_types == {"bull"}
    assert range_types == {"range"}

    assert len(btc["groups"]["bull"]) >= 1
    assert len(btc["groups"]["range"]) >= 1
