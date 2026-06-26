"""Recomendações de seleção por ativo e regime — IA de Seleção."""
from __future__ import annotations

from typing import Any

from atlas.strategies.metadata import BACKTEST_MATRIX_GROUPS, get_market_type
from atlas.strategies.mm200_trend_v2 import strategy_display_name

SLOTS_PER_ASSET = 6
TREND_SLOTS = 3
RANGE_SLOTS = 3

PACK_META: dict[str, dict[str, str]] = {
    "bull_range": {
        "label": "Alta + Lateral",
        "description": "3 estratégias de tendência de alta + 3 laterais — ideal em mercado bull ou transição.",
        "route": "/estrategias-alta",
        "peer_route": "/estrategias-lateral",
    },
    "bear_range": {
        "label": "Baixa + Lateral",
        "description": "3 estratégias de tendência de baixa + 3 laterais — ideal em mercado bear ou consolidação.",
        "route": "/estrategias-baixa",
        "peer_route": "/estrategias-lateral",
    },
}


def _item_score(item: dict[str, Any]) -> float:
    metrics = item.get("metrics") or {}
    atlas = float(metrics.get("atlas_score") or 0)
    if atlas > 0:
        return atlas
    pf = float(metrics.get("profit_factor") or 0)
    ret = float(metrics.get("total_return_pct") or 0)
    return pf * 20 + ret * 0.5


def _best_per_strategy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        sid = str(row.get("strategy") or "")
        if not sid:
            continue
        score = _item_score(row)
        prev = by_id.get(sid)
        if prev is None or score > _item_score(prev):
            by_id[sid] = row
    return sorted(by_id.values(), key=_item_score, reverse=True)


def _row_to_pick(row: dict[str, Any], *, base: str) -> dict[str, Any]:
    metrics = row.get("metrics") or {}
    return {
        "strategy": row.get("strategy"),
        "name": row.get("strategy_label") or strategy_display_name(str(row.get("strategy") or "")),
        "timeframe": str(row.get("timeframe") or "4h").lower(),
        "quote": "USDT",
        "base": base,
        "enabled": True,
        "market_type": row.get("market_type") or get_market_type(str(row.get("strategy") or "")),
        "atlas_score": round(float(metrics.get("atlas_score") or 0), 1) or None,
        "pf": round(float(metrics.get("profit_factor") or 0), 2) or None,
        "winrate": round(float(metrics.get("win_rate_pct") or 0), 1) or None,
        "dd": round(float(metrics.get("max_drawdown_pct") or 0), 1) or None,
        "return_pct": round(float(metrics.get("total_return_pct") or 0), 2) or None,
        "source": "backtest",
    }


def _default_pick(strategy: str, *, base: str, market_type: str) -> dict[str, Any]:
    return {
        "strategy": strategy,
        "name": strategy_display_name(strategy),
        "timeframe": "4h",
        "quote": "USDT",
        "base": base,
        "enabled": True,
        "market_type": market_type,
        "atlas_score": None,
        "pf": None,
        "winrate": None,
        "dd": None,
        "return_pct": None,
        "source": "default",
    }


def _fill_trend(picks: list[dict[str, Any]], *, base: str, trend_type: str) -> list[dict[str, Any]]:
    seen = {str(p["strategy"]) for p in picks}
    out = list(picks)
    for sid in BACKTEST_MATRIX_GROUPS.get(trend_type, ()):
        if len(out) >= TREND_SLOTS:
            break
        if sid in seen:
            continue
        out.append(_default_pick(sid, base=base, market_type=trend_type))
        seen.add(sid)
    return out[:TREND_SLOTS]


def _fill_range(picks: list[dict[str, Any]], *, base: str) -> list[dict[str, Any]]:
    seen = {str(p["strategy"]) for p in picks}
    out = list(picks)
    for sid in BACKTEST_MATRIX_GROUPS.get("range", ()):
        if len(out) >= RANGE_SLOTS:
            break
        if sid in seen:
            continue
        out.append(_default_pick(sid, base=base, market_type="range"))
        seen.add(sid)
    return out[:RANGE_SLOTS]


def _build_pack(
    *,
    base: str,
    trend_type: str,
    trend_rows: list[dict[str, Any]],
    range_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    trend_best = _best_per_strategy(trend_rows)
    range_best = _best_per_strategy(range_rows)

    trend_picks = [_row_to_pick(row, base=base) for row in trend_best[:TREND_SLOTS]]
    range_picks = [_row_to_pick(row, base=base) for row in range_best[:RANGE_SLOTS]]

    trend_slots = _fill_trend(trend_picks, base=base, trend_type=trend_type)
    range_slots = _fill_range(range_picks, base=base)
    slots = trend_slots + range_slots

    meta = PACK_META[f"{trend_type}_range"]

    return {
        "id": f"{trend_type}_range",
        "label": meta["label"],
        "description": meta["description"],
        "route": meta["route"],
        "peer_route": meta["peer_route"],
        "trend_type": trend_type,
        "slots": slots,
        "backtest_count": sum(1 for s in slots if s.get("source") == "backtest"),
    }


def _group_ranked(rows: list[dict[str, Any]], *, limit: int = 6) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(_best_per_strategy(rows)[:limit], start=1):
        metrics = row.get("metrics") or {}
        out.append(
            {
                "rank": i,
                "strategy": row.get("strategy"),
                "name": row.get("strategy_label") or strategy_display_name(str(row.get("strategy") or "")),
                "timeframe": str(row.get("timeframe") or "4h").lower(),
                "market_type": row.get("market_type") or get_market_type(str(row.get("strategy") or "")),
                "atlas_score": round(float(metrics.get("atlas_score") or 0), 1) or None,
                "pf": round(float(metrics.get("profit_factor") or 0), 2),
                "winrate": round(float(metrics.get("win_rate_pct") or 0), 1),
                "dd": round(float(metrics.get("max_drawdown_pct") or 0), 1),
                "return_pct": round(float(metrics.get("total_return_pct") or 0), 2),
            }
        )
    return out


def build_selection_payload(matrix: dict[str, Any]) -> dict[str, Any]:
    items = [i for i in (matrix.get("items") or []) if i.get("ok")]
    by_asset = matrix.get("by_asset") or {}
    assets_out: list[dict[str, Any]] = []

    for base in ("BTC", "ETH"):
        asset_slice = by_asset.get(base) or {}
        asset_items = asset_slice.get("items") or [
            i for i in items if str(i.get("base_asset") or "BTC").upper() == base
        ]

        bull_rows = [i for i in asset_items if (i.get("market_type") or get_market_type(str(i.get("strategy") or ""))) == "bull"]
        bear_rows = [i for i in asset_items if (i.get("market_type") or get_market_type(str(i.get("strategy") or ""))) == "bear"]
        range_rows = [i for i in asset_items if (i.get("market_type") or get_market_type(str(i.get("strategy") or ""))) == "range"]

        best_score_row = asset_slice.get("best_score")
        atlas = 50
        if isinstance(best_score_row, dict):
            atlas = int(float((best_score_row.get("metrics") or {}).get("atlas_score") or 50))

        assets_out.append(
            {
                "base": base,
                "atlas_score": max(0, min(100, atlas)),
                "total_backtests": len(asset_items),
                "groups": {
                    "bull": _group_ranked(bull_rows),
                    "bear": _group_ranked(bear_rows),
                    "range": _group_ranked(range_rows),
                },
                "packs": {
                    "bull_range": _build_pack(
                        base=base,
                        trend_type="bull",
                        trend_rows=bull_rows,
                        range_rows=range_rows,
                    ),
                    "bear_range": _build_pack(
                        base=base,
                        trend_type="bear",
                        trend_rows=bear_rows,
                        range_rows=range_rows,
                    ),
                },
            }
        )

    return {
        "slots_per_asset": SLOTS_PER_ASSET,
        "trend_slots": TREND_SLOTS,
        "range_slots": RANGE_SLOTS,
        "assets": assets_out,
    }
