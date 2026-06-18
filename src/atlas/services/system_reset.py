"""Apaga dados de teste/backtest e opcionalmente reseta demo paper."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from atlas.core.env import project_root
from atlas.core.models import TradingMode


@dataclass
class ResetOptions:
    reports: bool = True
    ohlcv_cache: bool = False
    paper_demo: bool = False


@dataclass
class ResetResult:
    deleted_files: list[str] = field(default_factory=list)
    cleared_files: list[str] = field(default_factory=list)
    risk_counters_reset: bool = False
    quantum_state_cleared: bool = False


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def reset_system_data(options: ResetOptions) -> ResetResult:
    root = project_root()
    result = ResetResult()

    if options.reports:
        reports_dir = root / "data" / "reports"
        if reports_dir.is_dir():
            for pattern in ("*_report.json", "*_walkforward.json", "*.md", "*.zip"):
                for path in reports_dir.glob(pattern):
                    if path.is_file():
                        path.unlink(missing_ok=True)
                        result.deleted_files.append(_rel(path, root))
            exports_dir = reports_dir / "exports"
            if exports_dir.is_dir():
                for path in exports_dir.rglob("*"):
                    if path.is_file():
                        path.unlink(missing_ok=True)
                        result.deleted_files.append(_rel(path, root))

    if options.ohlcv_cache:
        cache_dir = root / "data" / "cache"
        if cache_dir.is_dir():
            for path in cache_dir.glob("*.csv"):
                path.unlink(missing_ok=True)
                result.deleted_files.append(_rel(path, root))

    if options.paper_demo:
        journal_path = root / "data" / "journal" / f"{TradingMode.PAPER.value}.jsonl"
        if journal_path.is_file():
            journal_path.write_text("", encoding="utf-8")
            result.cleared_files.append(_rel(journal_path, root))

        balance_path = root / "data" / "runtime" / f"balance_{TradingMode.PAPER.value}.jsonl"
        if balance_path.is_file():
            balance_path.write_text("", encoding="utf-8")
            result.cleared_files.append(_rel(balance_path, root))

        quantum_path = root / "data" / "runtime" / "quantum_state.json"
        if quantum_path.is_file():
            quantum_path.unlink(missing_ok=True)
            result.quantum_state_cleared = True
            result.deleted_files.append(_rel(quantum_path, root))

        from atlas.runtime.risk_store import reset_risk_counters

        reset_risk_counters()
        result.risk_counters_reset = True

    return result
