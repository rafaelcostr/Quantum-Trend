"""Gates de aprovação — Backtest, Paper e Live."""
from __future__ import annotations

from typing import Any


def promotion_checklist_backtest(values: dict[str, Any]) -> list[dict[str, Any]]:
    pf = float(values.get("profit_factor", 0))
    dd = float(values.get("max_drawdown_pct", 1))
    win_rate = float(values.get("win_rate", 0))
    if win_rate > 1:
        win_rate /= 100.0
    trades = int(values.get("total_trades", values.get("trades", 0)))
    return [
        {"label": "Profit Factor > 1.4", "ok": pf > 1.4, "value": f"{pf:.2f}", "stage": "backtest"},
        {"label": "Win Rate > 50%", "ok": win_rate > 0.50, "value": f"{win_rate:.1%}", "stage": "backtest"},
        {"label": "Drawdown < 20%", "ok": dd < 0.20, "value": f"{dd:.1%}", "stage": "backtest"},
        {"label": "Trades registrados", "ok": trades > 0, "value": str(trades), "stage": "backtest"},
    ]


def promotion_checklist_paper(values: dict[str, Any]) -> list[dict[str, Any]]:
    pf = float(values.get("profit_factor", 0))
    dd = float(values.get("max_drawdown_pct", 1))
    trades = int(values.get("total_trades", values.get("trades", 0)))
    return [
        {"label": "Mínimo 50 trades", "ok": trades >= 50, "value": str(trades), "stage": "paper"},
        {"label": "Profit Factor > 1.5", "ok": pf > 1.5, "value": f"{pf:.2f}", "stage": "paper"},
        {"label": "Drawdown < 15%", "ok": dd < 0.15, "value": f"{dd:.1%}", "stage": "paper"},
    ]


def promotion_checklist_live_operational() -> list[dict[str, Any]]:
    return [
        {
            "label": "Capital inicial reduzido",
            "ok": True,
            "value": "Liberar fração do capital e monitorar",
            "stage": "live",
        },
        {
            "label": "Monitoramento contínuo",
            "ok": True,
            "value": "Health Score e drawdown em tempo real",
            "stage": "live",
        },
    ]


def merge_promotion_checklists(*checklists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for checklist in checklists:
        merged.extend(checklist)
    return merged
