"""Metadados das estrategias — tipo, versao e classificacao."""
from __future__ import annotations

from typing import Any

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


def parse_strategy_from_report_name(report_stem: str) -> tuple[str, str | None]:
    """Extrai estrategia e timeframe de nomes como mm200_trend_v2_4h_report."""
    name = report_stem.removesuffix("_report") if report_stem.endswith("_report") else report_stem
    timeframe: str | None = None
    for tf in ("4h", "1d", "1h"):
        suffix = f"_{tf}"
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            timeframe = tf
            break
    if name == "backtest":
        name = "unknown"
    return name, timeframe


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
