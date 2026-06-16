"""Simbolos de mercado e nomes de relatorios — sem dependencia do dashboard."""
from __future__ import annotations

QUOTE_ASSETS = ("USDT", "USDC")
REPORT_QUOTES = ("usdt", "usdc")
REPORT_TIMEFRAMES = ("4h", "1d", "1h")


def quote_from_symbol(symbol: str, default: str = "USDT") -> str:
    q = symbol.split("/")[-1].upper()
    return q if q in QUOTE_ASSETS else default


def report_name_stem(strategy: str, timeframe: str, quote: str) -> str:
    """Nome do JSON: range_hunter_v2_4h_usdt_report"""
    return f"{strategy}_{timeframe.lower()}_{quote.lower()}_report"


def parse_strategy_from_report_name(report_stem: str) -> tuple[str, str | None, str | None]:
    """Extrai estrategia, timeframe e quote de nomes como range_hunter_v2_4h_usdt_report."""
    name = report_stem.removesuffix("_report") if report_stem.endswith("_report") else report_stem
    quote: str | None = None
    for q in REPORT_QUOTES:
        suffix = f"_{q}"
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            quote = q.upper()
            break

    timeframe: str | None = None
    for tf in REPORT_TIMEFRAMES:
        suffix = f"_{tf}"
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            timeframe = tf
            break

    if name == "backtest":
        name = "unknown"
    return name, timeframe, quote
