from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from atlas.core.env import project_root
from atlas.intelligence.analyzer import analyze_path
from atlas.intelligence.metrics import discover_reports
from atlas.research.reports import load_latest_report


def _serialize(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def get_strategy_analysis(strategy_name: str | None = None) -> dict[str, Any] | None:
    reports_dir = project_root() / "data" / "reports"
    if strategy_name:
        report = load_latest_report(strategy_name)
        if not report:
            return None
        path = reports_dir / f"{strategy_name}_report.json"
        if not path.is_file():
            paths = list(reports_dir.glob(f"*{strategy_name}*_report.json"))
            path = paths[-1] if paths else path
    else:
        paths = discover_reports(reports_dir)
        if not paths:
            return None
        path = paths[-1]

    if not path.is_file():
        return None

    analysis = analyze_path(path, reports_dir=reports_dir)
    return _serialize(analysis)


def enrich_intelligence_summary(summary: dict, strategy_name: str | None = None) -> dict:
    try:
        analysis = get_strategy_analysis(strategy_name)
    except Exception:
        analysis = None
    if analysis and analysis.get("level1"):
        l1 = analysis["level1"]
        summary["overall_score"] = int(l1.get("atlas_score", summary.get("overall_score", 0)))
        summary["analysis"] = {
            "strategy": analysis.get("strategy"),
            "market": analysis.get("market"),
            "timeframe": analysis.get("timeframe"),
            "level1": l1,
            "level2": analysis.get("level2"),
            "level3": analysis.get("level3"),
        }
    return summary
