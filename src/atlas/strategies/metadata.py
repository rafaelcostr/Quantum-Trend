"""Metadados das estrategias — tipo, versao e classificacao."""
from __future__ import annotations

import json
from atlas.core.symbols import parse_strategy_from_report_name, quote_from_symbol

STRATEGY_METADATA: dict[str, dict[str, str]] = {
    "range_hunter_v1": {"type": "Mean Reversion", "version": "1.0.0"},
    "range_hunter_v2": {"type": "Mean Reversion", "version": "2.0.0"},
    "bb_squeeze_v1": {"type": "Breakout", "version": "1.0.0"},
    "regime_switching_v1": {"type": "Regime Switching", "version": "1.0.0"},
    "mm200_trend_v1": {"type": "Trend Following", "version": "1.0.0"},
    "mm200_trend_v2": {"type": "Trend Following", "version": "2.0.0"},
    "mm200_daily_macro_v1": {"type": "Trend Following", "version": "1.0.0"},
    "portfolio_macro_micro_v1": {"type": "Multi-Strategy", "version": "1.0.0"},
}


def get_strategy_metadata(strategy_name: str) -> dict[str, str]:
    return STRATEGY_METADATA.get(
        strategy_name,
        {"type": "Unknown", "version": "1.0.0"},
    )


def strategy_type_label(strategy_name: str) -> str:
    return get_strategy_metadata(strategy_name)["type"]


def strategy_version(strategy_name: str) -> str:
    return get_strategy_metadata(strategy_name)["version"]


def config_file_for_strategy(strategy_name: str) -> str:
    """Melhor palpite do YAML usado no backtest."""
    mapping = {
        "range_hunter_v1": "config/backtest.yaml",
        "range_hunter_v2": "config/backtest_v2.yaml",
        "bb_squeeze_v1": "config/backtest_v3.yaml",
        "regime_switching_v1": "config/backtest_v2_1.yaml",
        "mm200_trend_v1": "config/backtest_v2_2.yaml",
        "mm200_trend_v2": "config/backtest_mm200_v2.yaml",
        "mm200_daily_macro_v1": "config/backtest_daily_macro.yaml",
        "portfolio_macro_micro_v1": "config/backtest_portfolio.yaml",
    }
    return mapping.get(strategy_name, f"config/backtest_{strategy_name}.yaml")


def position_size_label(sizing_mode: str, risk_per_trade: float) -> str:
    if sizing_mode == "full_equity":
        return "100% equity"
    return f"{risk_per_trade:.1%} per trade ({sizing_mode})"


def report_display_label(path: Path) -> str:
    """Rotulo legivel para dropdowns (estrategia, timeframe, tipo)."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        meta = raw.get("metadata") or {}
        if meta.get("strategy"):
            strategy = str(meta["strategy"])
            tf = meta.get("timeframe")
            market = str(meta.get("market") or "BTC/USDT")
            quote = quote_from_symbol(market)
            stype = meta.get("strategy_type") or get_strategy_metadata(strategy).get("type", "")
            base = f"{strategy} ({tf}) BTC/{quote}" if tf else f"{strategy} BTC/{quote}"
            if stype and stype != "Unknown":
                return f"{base} — {stype}"
            return base
    except (OSError, json.JSONDecodeError, KeyError):
        pass

    strategy, tf, quote = parse_strategy_from_report_name(path.stem)
    meta = get_strategy_metadata(strategy)
    if strategy == "unknown":
        return f"{path.stem} (antigo — rode backtest em Pesquisa)"
    q = quote or "USDT"
    base = f"{strategy} ({tf}) BTC/{q}" if tf else f"{strategy} BTC/{q}"
    stype = meta.get("type", "Unknown")
    if stype != "Unknown":
        return f"{base} — {stype}"
    return base


def report_select_options(reports_dir: Path) -> list[tuple[str, Path]]:
    """Lista (rotulo, path) unica para selectbox — evita colisao de nomes."""
    from atlas.intelligence.metrics import discover_reports

    paths = discover_reports(reports_dir)
    seen: dict[str, int] = {}
    options: list[tuple[str, Path]] = []
    for path in paths:
        label = report_display_label(path)
        if label in seen:
            seen[label] += 1
            label = f"{label} · {path.name}"
        else:
            seen[label] = 1
        options.append((label, path))
    return options
