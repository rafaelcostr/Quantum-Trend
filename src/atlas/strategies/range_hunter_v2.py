from __future__ import annotations

from atlas.strategies.range_hunter_v1 import RangeHunterV1


class RangeHunterV2(RangeHunterV1):
    """Range Hunter with mandatory support confluence at entry."""

    name = "range_hunter_v2"

    def __init__(
        self,
        rsi_long_max: float = 38.0,
        adx_max: float = 25.0,
        stop_pct: float = 0.025,
    ) -> None:
        super().__init__(
            rsi_long_max=rsi_long_max,
            adx_max=adx_max,
            stop_pct=stop_pct,
            require_sr=True,
        )


def build_range_hunter_v2(params: dict) -> RangeHunterV2:
    return RangeHunterV2(
        rsi_long_max=float(params.get("rsi_long_max", 38)),
        adx_max=float(params.get("adx_max", 25)),
        stop_pct=float(params.get("stop_pct", 0.025)),
    )
