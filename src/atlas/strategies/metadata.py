"""Metadados das estratégias."""
from __future__ import annotations

from pathlib import Path

PRIMARY_STRATEGIES = (
    "quantum_trend_pro",
)

# Módulos de entrada reutilizados como estratégias standalone — somente pesquisa/comparação
ENTRY_MODULE_LEGACY_STRATEGIES = frozenset({
    "pullback_ema20_v1",
    "breakout_high20_v1",
    "supertrend_mm200_v1",
})

BEAR_STRATEGIES = frozenset({
    "pullback_short_v1",
    "breakout_down_v1",
    "supertrend_bear_v1",
})

RANGE_STRATEGIES = frozenset({
    "range_hunter_v1",
    "range_hunter_v2",
    "bb_squeeze_v1",
    "regime_switching_v1",
})

# Matriz de backtests — todas as estratégias operacionais + legado de pesquisa
BACKTEST_MATRIX_GROUPS: dict[str, tuple[str, ...]] = {
    "bull": (
        "pullback_ema20_v1",
        "breakout_high20_v1",
        "supertrend_mm200_v1",
        "quantum_trend_pro",
        "mm200_trend_v1",
        "mm200_trend_v2",
        "mm200_daily_macro_v1",
        "portfolio_macro_micro_v1",
    ),
    "bear": (
        "pullback_short_v1",
        "breakout_down_v1",
        "supertrend_bear_v1",
    ),
    "range": (
        "range_hunter_v1",
        "range_hunter_v2",
        "bb_squeeze_v1",
        "regime_switching_v1",
    ),
}

# Estratégias legacy de pesquisa (8)
LEGACY_STRATEGIES = frozenset({
    "range_hunter_v1",
    "range_hunter_v2",
    "bb_squeeze_v1",
    "regime_switching_v1",
    "mm200_trend_v1",
    "mm200_trend_v2",
    "mm200_daily_macro_v1",
    "portfolio_macro_micro_v1",
})

STRATEGY_METADATA: dict[str, dict[str, str]] = {
    "quantum_trend_pro": {"type": "QuantumTrend Pro Core", "version": "1.0.0", "tier": "primary"},
    "pullback_ema20_v1": {
        "type": "Entry Module · Pullback",
        "version": "1.0.0",
        "tier": "entry_module_legacy",
        "market_type": "bull",
        "strategy_category": "bull",
        "note": "Use quantum_trend_pro — módulo Pullback",
    },
    "breakout_high20_v1": {
        "type": "Entry Module · Breakout",
        "version": "1.0.0",
        "tier": "entry_module_legacy",
        "market_type": "bull",
        "strategy_category": "bull",
        "note": "Use quantum_trend_pro — módulo Breakout",
    },
    "supertrend_mm200_v1": {
        "type": "Entry Module · Supertrend",
        "version": "1.0.0",
        "tier": "entry_module_legacy",
        "market_type": "bull",
        "strategy_category": "bull",
        "note": "Use quantum_trend_pro — módulo Supertrend",
    },
    "pullback_short_v1": {
        "type": "Bear Strategy · Pullback Short",
        "version": "1.0.0",
        "tier": "bear",
        "market_type": "bear",
        "strategy_category": "bear",
    },
    "breakout_down_v1": {
        "type": "Bear Strategy · Breakout Down",
        "version": "1.0.0",
        "tier": "bear",
        "market_type": "bear",
        "strategy_category": "bear",
    },
    "supertrend_bear_v1": {
        "type": "Bear Strategy · Supertrend Bear",
        "version": "1.0.0",
        "tier": "bear",
        "market_type": "bear",
        "strategy_category": "bear",
    },
    "range_hunter_v1": {"type": "Mean Reversion", "version": "1.0.0", "tier": "legacy", "market_type": "range", "strategy_category": "range"},
    "range_hunter_v2": {"type": "Mean Reversion", "version": "2.0.0", "tier": "legacy", "market_type": "range", "strategy_category": "range"},
    "bb_squeeze_v1": {"type": "Breakout", "version": "1.0.0", "tier": "legacy", "market_type": "range", "strategy_category": "range"},
    "regime_switching_v1": {"type": "Regime Switching", "version": "1.0.0", "tier": "legacy", "market_type": "range", "strategy_category": "range"},
    "mm200_trend_v1": {"type": "Trend Following", "version": "1.0.0", "tier": "legacy"},
    "mm200_trend_v2": {"type": "Trend Following", "version": "2.0.0", "tier": "legacy"},
    "mm200_daily_macro_v1": {"type": "Trend Following", "version": "1.0.0", "tier": "legacy"},
    "portfolio_macro_micro_v1": {"type": "Multi-Strategy", "version": "1.0.0", "tier": "legacy"},
}


def is_legacy_strategy(name: str) -> bool:
    return name in LEGACY_STRATEGIES


def is_entry_module_legacy(name: str) -> bool:
    return name in ENTRY_MODULE_LEGACY_STRATEGIES


def is_bull_entry_module(name: str) -> bool:
    return name in ENTRY_MODULE_LEGACY_STRATEGIES


def is_bear_strategy(name: str) -> bool:
    return name in BEAR_STRATEGIES


def is_range_strategy(name: str) -> bool:
    return name in RANGE_STRATEGIES


def get_market_type(strategy_name: str) -> str:
    meta = get_strategy_metadata(strategy_name)
    if meta.get("market_type"):
        return str(meta["market_type"])
    if strategy_name in BEAR_STRATEGIES:
        return "bear"
    if strategy_name in RANGE_STRATEGIES:
        return "range"
    if strategy_name in ENTRY_MODULE_LEGACY_STRATEGIES or strategy_name.startswith("mm200"):
        return "bull"
    return "bull"


def get_strategy_category(strategy_name: str) -> str:
    meta = get_strategy_metadata(strategy_name)
    if meta.get("strategy_category"):
        return str(meta["strategy_category"])
    return get_market_type(strategy_name)


def is_research_only(name: str) -> bool:
    return is_legacy_strategy(name) or is_entry_module_legacy(name)


def list_primary_strategies() -> list[str]:
    return list(PRIMARY_STRATEGIES)


def list_backtest_matrix_strategies() -> list[str]:
    """Estratégias incluídas em Testar todas (1H + 4H + 1D)."""
    names: list[str] = []
    seen: set[str] = set()
    for group in BACKTEST_MATRIX_GROUPS.values():
        for name in group:
            if name not in seen:
                seen.add(name)
                names.append(name)
    return names


def group_backtest_matrix_items(items: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {key: [] for key in BACKTEST_MATRIX_GROUPS}
    for item in items:
        strategy = str(item.get("strategy") or "")
        market = get_market_type(strategy) if strategy else "bull"
        if market not in grouped:
            market = "bull"
        grouped[market].append(item)
    return grouped


def backtest_matrix_group_labels() -> dict[str, str]:
    return {
        "bull": "Estratégias de Alta",
        "bear": "Estratégias de Baixa",
        "range": "Estratégias Laterais",
    }


def get_strategy_metadata(strategy_name: str) -> dict[str, str]:
    meta = STRATEGY_METADATA.get(strategy_name, {"type": "Unknown", "version": "1.0.0", "tier": "legacy"})
    return meta


def position_size_label(sizing_mode: str, risk_per_trade: float) -> str:
    if sizing_mode == "full_equity":
        return "100% equity"
    return f"{risk_per_trade:.1%} per trade ({sizing_mode})"


def config_file_for_strategy(strategy_name: str) -> str:
    mapping = {
        "range_hunter_v1": "config/backtest.yaml",
        "range_hunter_v2": "config/backtest_v2.yaml",
        "bb_squeeze_v1": "config/backtest_v3.yaml",
        "regime_switching_v1": "config/backtest_v2_1.yaml",
        "mm200_trend_v1": "config/backtest_v2_2.yaml",
        "mm200_trend_v2": "config/backtest_mm200_v2.yaml",
        "mm200_daily_macro_v1": "config/backtest_daily_macro.yaml",
        "portfolio_macro_micro_v1": "config/backtest_portfolio.yaml",
        "pullback_ema20_v1": "config/backtest_pullback_ema20_v1.yaml",
        "breakout_high20_v1": "config/backtest_breakout_high20_v1.yaml",
        "supertrend_mm200_v1": "config/backtest_supertrend_mm200_v1.yaml",
        "pullback_short_v1": "config/backtest_pullback_short_v1.yaml",
        "breakout_down_v1": "config/backtest_breakout_down_v1.yaml",
        "supertrend_bear_v1": "config/backtest_supertrend_bear_v1.yaml",
        "quantum_trend_pro": "config/backtest_quantum_trend_pro.yaml",
    }
    return mapping.get(strategy_name, f"config/backtest_{strategy_name}.yaml")


def report_display_label(path: Path) -> str:
    from atlas.core.symbols import parse_strategy_from_report_name

    strategy, tf, quote, _base = parse_strategy_from_report_name(path.stem)
    meta = get_strategy_metadata(strategy)
    parts = [strategy]
    if tf:
        parts.append(tf)
    if quote:
        parts.append(quote)
    label = " · ".join(parts)
    stype = meta.get("type")
    if stype and stype != "Unknown":
        label += f" ({stype})"
    is_legacy = path.stem == "backtest_report" or strategy == "unknown"
    if is_legacy:
        label += " — backtest antigo"
    return label
