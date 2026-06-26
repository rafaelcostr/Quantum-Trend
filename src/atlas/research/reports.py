"""Helpers para ler/gravar relatorios de backtest."""
from __future__ import annotations

import json
from pathlib import Path

from atlas.core.env import project_root
from atlas.core.symbols import quote_from_symbol, report_json_candidates, report_name_stem


def report_path_for_config(config) -> Path:
    quote = quote_from_symbol(config.exchange.symbol)
    base = config.exchange.symbol.split("/")[0]
    stem = report_name_stem(config.strategy.name, config.exchange.timeframe, quote, base)
    reports_dir = project_root() / "data" / "reports"
    for filename in report_json_candidates(stem):
        path = reports_dir / filename
        if path.is_file():
            return path
    return reports_dir / report_json_candidates(stem)[0]


def load_report_for_config(config) -> dict | None:
    """Carrega relatório exato da estratégia/timeframe ativos, com fallback por estratégia."""
    exact = report_path_for_config(config)
    if exact.is_file():
        raw = json.loads(exact.read_text(encoding="utf-8"))
        return _normalize_report(raw)
    return load_latest_report(config.strategy.name)


def load_report_by_strategy_timeframe(
    strategy: str,
    timeframe: str,
    *,
    quote: str = "USDT",
    base: str = "BTC",
) -> dict | None:
    stem = report_name_stem(strategy, timeframe.lower(), quote, base)
    reports_dir = project_root() / "data" / "reports"
    for filename in report_json_candidates(stem):
        path = reports_dir / filename
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            return _normalize_report(raw)
    legacy_stem = report_name_stem(strategy, timeframe.lower(), quote)
    for filename in report_json_candidates(legacy_stem):
        path = reports_dir / filename
        if base.upper() == "BTC" and path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            return _normalize_report(raw)
    return load_latest_report(strategy)


def load_latest_report(strategy: str) -> dict | None:
    reports_dir = project_root() / "data" / "reports"
    legacy = reports_dir / f"{strategy}_report.json"
    if legacy.is_file():
        return _normalize_report(json.loads(legacy.read_text(encoding="utf-8")))

    matches = sorted(reports_dir.glob(f"{strategy}_*_report.json"))
    if not matches:
        return None
    raw = json.loads(matches[-1].read_text(encoding="utf-8"))
    return _normalize_report(raw)


def _normalize_report(raw: dict) -> dict:
    if "metrics" in raw:
        return raw
    stats = raw.get("statistics") or {}
    win_rate = float(stats.get("win_rate", 0))
    return {
        **raw,
        "metrics": {
            "total_return_pct": round(float(stats.get("net_profit_pct", 0)) * 100, 2),
            "profit_factor": round(float(stats.get("profit_factor", 0)), 2),
            "max_drawdown_pct": round(float(stats.get("max_drawdown_pct", 0)) * 100, 2),
            "sharpe": round(float(stats.get("sharpe_ratio") or 0), 2),
            "win_rate_pct": round(win_rate * 100, 2),
            "trades": int(stats.get("total_trades", 0)),
            "expectancy": round(float(stats.get("avg_trade_pct", 0)), 4),
            "atlas_score": 0,
        },
    }
