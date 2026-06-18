"""Score Explanation Engine — detalhamento do Alignment Score."""
from __future__ import annotations

from typing import Any

from atlas.platform.store import patch_platform_state

COMPONENT_LABELS = {
    "trend_alignment": "Trend Alignment",
    "adx_strength": "ADX Strength",
    "volume_confirmation": "Volume",
    "volatility_regime": "Volatility",
    "momentum_confirmation": "Momentum",
}

WEIGHTS = {
    "trend_alignment": 35.0,
    "adx_strength": 20.0,
    "volume_confirmation": 15.0,
    "volatility_regime": 15.0,
    "momentum_confirmation": 15.0,
}


def build_score_explanation(
    *,
    total: float,
    breakdown: dict[str, float],
    threshold: int,
) -> dict[str, Any]:
    components = []
    for key, max_pts in WEIGHTS.items():
        pts = float(breakdown.get(key, 0))
        components.append(
            {
                "key": key,
                "label": COMPONENT_LABELS.get(key, key),
                "score": round(pts, 1),
                "max": max_pts,
                "pct": round((pts / max_pts) * 100, 1) if max_pts else 0,
            }
        )
    explanation = {
        "total": round(total, 1),
        "max": 100,
        "threshold": threshold,
        "eligible": total >= threshold,
        "components": components,
        "summary": f"Alignment Score {total:.0f}/100 (mínimo {threshold})",
    }
    return explanation


def persist_score_explanation(explanation: dict[str, Any], *, strategy: str) -> dict[str, Any]:
    from datetime import datetime, timezone

    payload = {**explanation, "strategy": strategy, "ts": datetime.now(timezone.utc).isoformat()}
    from atlas.platform.store import load_platform_state, save_platform_state

    data = load_platform_state()
    history = list(data.get("score_explanations") or [])
    history.insert(0, payload)
    data["score_explanations"] = history[:100]
    data["latest_score_explanation"] = payload
    save_platform_state(data)
    return payload
