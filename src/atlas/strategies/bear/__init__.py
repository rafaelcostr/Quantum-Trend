"""Estratégias Bear Market — módulo independente das estratégias Bull."""

from atlas.strategies.bear.breakout_down_v1 import BreakoutDownV1, build_breakout_down_v1
from atlas.strategies.bear.pullback_short_v1 import PullbackShortV1, build_pullback_short_v1
from atlas.strategies.bear.supertrend_bear_v1 import SupertrendBearV1, build_supertrend_bear_v1

BEAR_STRATEGY_BUILDERS = {
    "pullback_short_v1": build_pullback_short_v1,
    "breakout_down_v1": build_breakout_down_v1,
    "supertrend_bear_v1": build_supertrend_bear_v1,
}

__all__ = [
    "BEAR_STRATEGY_BUILDERS",
    "BreakoutDownV1",
    "PullbackShortV1",
    "SupertrendBearV1",
    "build_breakout_down_v1",
    "build_pullback_short_v1",
    "build_supertrend_bear_v1",
]
