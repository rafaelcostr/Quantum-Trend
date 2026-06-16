from __future__ import annotations

from atlas.strategies.bb_squeeze_v1 import BBSqueezeV1, build_bb_squeeze
from atlas.strategies.mm200_daily_macro_v1 import MM200DailyMacroV1, build_mm200_daily_macro_v1
from atlas.strategies.mm200_trend_v1 import MM200TrendV1, build_mm200_trend_v1
from atlas.strategies.mm200_trend_v2 import MM200TrendV2, build_mm200_trend_v2
from atlas.strategies.portfolio_v1 import PortfolioMacroMicroV1, build_portfolio_macro_micro_v1
from atlas.strategies.range_hunter_v1 import RangeHunterV1, build_range_hunter_v1
from atlas.strategies.range_hunter_v2 import RangeHunterV2, build_range_hunter_v2
from atlas.strategies.regime_switching_v1 import RegimeSwitchingV1, build_regime_switching_v1

STRATEGY_BUILDERS = {
    "range_hunter_v1": build_range_hunter_v1,
    "range_hunter_v2": build_range_hunter_v2,
    "bb_squeeze_v1": build_bb_squeeze,
    "regime_switching_v1": build_regime_switching_v1,
    "mm200_trend_v1": build_mm200_trend_v1,
    "mm200_trend_v2": build_mm200_trend_v2,
    "mm200_daily_macro_v1": build_mm200_daily_macro_v1,
    "portfolio_macro_micro_v1": build_portfolio_macro_micro_v1,
}


def build_strategy_from_config(name: str, params: dict):
    builder = STRATEGY_BUILDERS.get(name)
    if builder is None:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_BUILDERS)}")
    return builder(params)


__all__ = [
    "BBSqueezeV1",
    "MM200DailyMacroV1",
    "MM200TrendV1",
    "MM200TrendV2",
    "PortfolioMacroMicroV1",
    "RangeHunterV1",
    "RangeHunterV2",
    "RegimeSwitchingV1",
    "STRATEGY_BUILDERS",
    "build_strategy_from_config",
]
