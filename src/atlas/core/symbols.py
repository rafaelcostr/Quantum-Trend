"""Símbolos de mercado e nomes de relatórios."""
from __future__ import annotations

import re
from dataclasses import dataclass

QUOTE_ASSETS = ("USDT", "USDC")
OPERATED_BASES = ("BTC", "ETH")
REPORT_QUOTES = ("usdt", "usdc")
REPORT_TIMEFRAMES = ("4h", "1d", "1h")
BACKTEST_REPORT_JSON = re.compile(
    r"^.+_(?:1h|4h|1d)_(?:usdt|usdc)(?:_(?:btc|eth))?(?:_report)?\.json$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NormalizedSymbol:
    """Representação canônica de símbolo independente da exchange."""

    base: str
    quote: str
    canonical: str
    exchange: str
    compact: str


def normalize_symbol(symbol: str, *, default_quote: str = "USDT") -> NormalizedSymbol:
    """Aceita BTC/USDT, BTCUSDT ou base isolada e devolve formatos padronizados."""
    raw = (symbol or "").strip().upper().replace("-", "/").replace("_", "/")
    if not raw:
        raw = f"BTC/{default_quote}"

    base: str
    quote: str
    if "/" in raw:
        left, right = raw.split("/", 1)
        base, quote = left.strip(), right.strip()
    else:
        quote = next((q for q in QUOTE_ASSETS if raw.endswith(q) and len(raw) > len(q)), default_quote.upper())
        base = raw[: -len(quote)] if raw.endswith(quote) and len(raw) > len(quote) else raw

    base = (base or "BTC").upper()
    quote = (quote or default_quote).upper()
    return NormalizedSymbol(
        base=base,
        quote=quote,
        canonical=f"{base}/{quote}",
        exchange=f"{base}/{quote}",
        compact=f"{base}{quote}",
    )


def compact_symbol(symbol: str) -> str:
    return normalize_symbol(symbol).compact


def quote_from_symbol(symbol: str, default: str = "USDT") -> str:
    q = normalize_symbol(symbol, default_quote=default).quote
    return q if q in QUOTE_ASSETS else default


def base_from_symbol(symbol: str, default: str = "BTC") -> str:
    base = normalize_symbol(symbol).base
    return base if base in OPERATED_BASES else default


def validate_operated_base(base: str) -> str:
    b = base.upper()
    if b not in OPERATED_BASES:
        raise ValueError(f"Ativo inválido: {base}. Use BTC ou ETH.")
    return b


def build_symbol(base: str, quote: str = "USDT") -> str:
    b = validate_operated_base(base)
    q = quote.upper()
    if q not in QUOTE_ASSETS:
        raise ValueError(f"Quote invalido: {quote}. Use USDT ou USDC.")
    return normalize_symbol(f"{b}/{q}").canonical


def operated_symbols(*, quote: str = "USDT") -> list[str]:
    q = quote.upper()
    if q not in QUOTE_ASSETS:
        q = "USDT"
    return [build_symbol(base, q) for base in OPERATED_BASES]


def operated_market_watchlist() -> list[str]:
    """Pares spot exibidos e monitorados (USDT)."""
    return operated_symbols(quote="USDT")


REPORT_BASES = ("btc", "eth")


def report_name_stem(strategy: str, timeframe: str, quote: str, base: str | None = None) -> str:
    stem = f"{strategy}_{timeframe.lower()}_{quote.lower()}"
    if base:
        stem = f"{stem}_{base.lower()}"
    return stem


def report_json_basename(stem: str) -> str:
    """Nome do arquivo JSON de backtest (sempre com sufixo _report)."""
    base = stem.removesuffix("_report") if stem.endswith("_report") else stem
    return f"{base}_report.json"


def report_json_candidates(stem: str) -> tuple[str, ...]:
    """Nomes possíveis ao ler relatórios (novo + legado sem _report)."""
    base = stem.removesuffix("_report") if stem.endswith("_report") else stem
    return (f"{base}_report.json", f"{base}.json")


def is_backtest_report_filename(filename: str) -> bool:
    lower = filename.lower()
    if "walkforward" in lower or lower.startswith("compare"):
        return False
    if BACKTEST_REPORT_JSON.match(filename):
        return True
    if not lower.endswith("_report.json"):
        return False
    stem = report_stem_from_filename(filename)
    strategy, _, _, _ = parse_strategy_from_report_name(stem)
    return strategy != "unknown"


def report_stem_from_filename(filename: str) -> str:
    return filename[:-5] if filename.lower().endswith(".json") else filename


def parse_strategy_from_report_name(report_stem: str) -> tuple[str, str | None, str | None, str | None]:
    name = report_stem.removesuffix("_report") if report_stem.endswith("_report") else report_stem
    quote: str | None = None
    base: str | None = None
    for b in REPORT_BASES:
        suffix = f"_{b}"
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            base = b.upper()
            break

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
    return name, timeframe, quote, base
