from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class ReportBundle:
    strategy: str
    statistics: dict[str, Any]
    trades: list[dict[str, Any]]
    equity_curve: list[dict[str, Any]]
    source_path: str
    metadata: dict[str, Any] = field(default_factory=dict)


def load_report(path: str | Path) -> ReportBundle:
    from atlas.research.report_metadata import metadata_from_report_path

    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    meta = metadata_from_report_path(path, raw)
    meta["source_path"] = str(path)
    strategy = str(meta.get("strategy") or path.stem.replace("_report", ""))
    return ReportBundle(
        strategy=strategy,
        statistics=raw.get("statistics", raw.get("metrics", {})),
        trades=raw.get("trades", []),
        equity_curve=raw.get("equity_curve", []),
        source_path=str(path),
        metadata=meta,
    )


def discover_reports(reports_dir: str | Path) -> list[Path]:
    reports_dir = Path(reports_dir)
    if not reports_dir.is_dir():
        return []
    return sorted(reports_dir.glob("*_report.json"))


def compute_expectancy(trades: list[dict[str, Any]], initial_capital: float) -> float:
    if not trades or initial_capital <= 0:
        return 0.0
    pnls = [float(t.get("pnl", 0)) for t in trades]
    return float(np.mean(pnls)) / initial_capital


def compute_cagr(equity_curve: list[dict[str, Any]], net_profit_pct: float) -> float | None:
    if len(equity_curve) < 2:
        return net_profit_pct
    try:
        start = datetime.fromisoformat(equity_curve[0]["timestamp"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(equity_curve[-1]["timestamp"].replace("Z", "+00:00"))
        years = (end - start).days / 365.25
        if years <= 0:
            return None
        final_mult = 1 + net_profit_pct
        if final_mult <= 0:
            return None
        return float(final_mult ** (1 / years) - 1)
    except (KeyError, ValueError, TypeError):
        return None


def period_bounds(equity_curve: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    if not equity_curve:
        return None, None
    try:
        return equity_curve[0]["timestamp"][:10], equity_curve[-1]["timestamp"][:10]
    except (KeyError, TypeError):
        return None, None


def years_tested(equity_curve: list[dict[str, Any]]) -> float | None:
    if len(equity_curve) < 2:
        return None
    try:
        start = datetime.fromisoformat(equity_curve[0]["timestamp"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(equity_curve[-1]["timestamp"].replace("Z", "+00:00"))
        return (end - start).days / 365.25
    except (KeyError, ValueError, TypeError):
        return None


def infer_initial_capital(statistics: dict[str, Any], trades: list[dict], equity_curve: list) -> float:
    net_profit = float(statistics.get("net_profit", 0))
    net_pct = float(statistics.get("net_profit_pct", 0))
    if net_pct != 0:
        return net_profit / net_pct
    if equity_curve:
        return float(equity_curve[0].get("equity", 10_000))
    return 10_000.0
