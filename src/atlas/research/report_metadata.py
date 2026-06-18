"""Metadados embutidos nos relatorios JSON de backtest."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atlas.core.config import AtlasConfig
from atlas.core.symbols import parse_strategy_from_report_name, quote_from_symbol
from atlas.strategies.metadata import config_file_for_strategy, get_strategy_metadata, position_size_label


def build_report_metadata(
    config: AtlasConfig,
    *,
    config_file: str | None = None,
    buy_hold_pct: float | None = None,
    report_name: str | None = None,
) -> dict[str, Any]:
    strategy = config.strategy.name
    meta = get_strategy_metadata(strategy)
    cfg_path = config_file or config_file_for_strategy(strategy)
    return {
        "strategy": strategy,
        "strategy_version": meta["version"],
        "strategy_type": meta["type"],
        "config_file": cfg_path,
        "market": config.exchange.symbol,
        "quote": quote_from_symbol(config.exchange.symbol),
        "timeframe": config.exchange.timeframe,
        "mode": config.mode.value,
        "risk_model": config.risk.sizing_mode,
        "position_size": position_size_label(config.risk.sizing_mode, config.risk.risk_per_trade),
        "risk_per_trade": config.risk.risk_per_trade,
        "initial_capital": config.risk.initial_capital,
        "fee_rate": config.execution.fee_rate,
        "slippage_rate": config.execution.slippage_rate,
        "buy_hold_pct": buy_hold_pct,
        "report_name": report_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def remove_stale_reports(
    out_dir: Path,
    *,
    strategy: str,
    timeframe: str,
    quote: str,
) -> list[str]:
    removed: list[str] = []
    if not out_dir.is_dir() or not strategy or strategy == "unknown":
        return removed
    quote = quote.upper()
    for path in list(out_dir.glob("*_report.json")):
        file_strategy, file_tf, file_quote = parse_strategy_from_report_name(path.stem)
        if file_strategy != strategy:
            continue
        if file_tf is not None and file_tf != timeframe:
            continue
        effective_quote = (file_quote or "USDT").upper()
        if effective_quote != quote:
            continue
        if file_quote is None and quote != "USDT":
            continue
        try:
            path.unlink()
            removed.append(path.name)
        except OSError:
            pass
    return removed


def metadata_from_report_path(path: Path, raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("metadata"):
        return dict(raw["metadata"])
    strategy, tf, file_quote = parse_strategy_from_report_name(path.stem)
    quote = file_quote or "USDT"
    meta = get_strategy_metadata(strategy)
    stats = raw.get("statistics", {})
    return {
        "strategy": strategy,
        "strategy_version": meta["version"],
        "strategy_type": meta["type"],
        "config_file": config_file_for_strategy(strategy),
        "market": f"BTC/{quote}",
        "quote": quote,
        "timeframe": tf or "4h",
        "mode": "backtest",
        "risk_model": "unknown",
        "position_size": "unknown",
        "fee_rate": None,
        "slippage_rate": None,
        "buy_hold_pct": None,
        "report_name": path.stem,
        "legacy_report": True,
        "net_profit_pct_hint": stats.get("net_profit_pct"),
    }
