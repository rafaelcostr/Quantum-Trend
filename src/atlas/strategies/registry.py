from __future__ import annotations

from atlas.quantum.core_strategy import build_quantum_trend_pro
from atlas.strategies.bear import BEAR_STRATEGY_BUILDERS
from atlas.strategies.bb_squeeze_v1 import BBSqueezeV1, build_bb_squeeze
from atlas.strategies.breakout_high20_v1 import BreakoutHigh20V1, build_breakout_high20_v1
from atlas.strategies.mm200_daily_macro_v1 import MM200DailyMacroV1, build_mm200_daily_macro_v1
from atlas.strategies.mm200_trend_v1 import MM200TrendV1, build_mm200_trend_v1
from atlas.strategies.mm200_trend_v2 import MM200TrendV2, build_mm200_trend_v2
from atlas.strategies.portfolio_v1 import PortfolioMacroMicroV1, build_portfolio_macro_micro_v1
from atlas.strategies.pullback_ema20_v1 import PullbackEma20V1, build_pullback_ema20_v1
from atlas.strategies.range_hunter_v1 import RangeHunterV1, build_range_hunter_v1
from atlas.strategies.range_hunter_v2 import RangeHunterV2, build_range_hunter_v2
from atlas.strategies.regime_switching_v1 import RegimeSwitchingV1, build_regime_switching_v1
from atlas.strategies.supertrend_mm200_v1 import SupertrendMm200V1, build_supertrend_mm200_v1

STRATEGY_BUILDERS = {
    "range_hunter_v1": build_range_hunter_v1,
    "range_hunter_v2": build_range_hunter_v2,
    "bb_squeeze_v1": build_bb_squeeze,
    "regime_switching_v1": build_regime_switching_v1,
    "mm200_trend_v1": build_mm200_trend_v1,
    "mm200_trend_v2": build_mm200_trend_v2,
    "mm200_daily_macro_v1": build_mm200_daily_macro_v1,
    "portfolio_macro_micro_v1": build_portfolio_macro_micro_v1,
    "pullback_ema20_v1": build_pullback_ema20_v1,
    "breakout_high20_v1": build_breakout_high20_v1,
    "supertrend_mm200_v1": build_supertrend_mm200_v1,
    "quantum_trend_pro": build_quantum_trend_pro,
    **BEAR_STRATEGY_BUILDERS,
}


def build_strategy_from_config(name: str, params: dict):
    builder = STRATEGY_BUILDERS.get(name)
    if builder is None:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_BUILDERS)}")
    return builder(params)


def list_strategies(*, include_legacy: bool = True) -> list[str]:
    names = list(STRATEGY_BUILDERS.keys())
    if include_legacy:
        return names
    from atlas.strategies.metadata import list_primary_strategies

    primary = set(list_primary_strategies())
    return [name for name in names if name in primary]


def get_signal_fn(name: str):
    """Compatibilidade legada — retorna wrapper para backtest simplificado."""
    strategy = build_strategy_from_config(name, {})

    def _fn(row, *, in_position: bool):
        from atlas.core.models import Candle, IndicatorSnapshot, Position, Side, SignalAction

        candle = Candle(
            timestamp=row["timestamp"].to_pydatetime()
            if hasattr(row["timestamp"], "to_pydatetime")
            else row["timestamp"],
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row.get("volume", 0)),
        )
        indicators = IndicatorSnapshot(
            timestamp=candle.timestamp,
            bb_upper=_f(row, "bb_upper"),
            bb_mid=_f(row, "bb_mid"),
            bb_lower=_f(row, "bb_lower"),
            rsi=_f(row, "rsi"),
            adx=_f(row, "adx"),
            atr=_f(row, "atr"),
            support=_f(row, "support"),
            resistance=_f(row, "resistance"),
            bb_width=_f(row, "bb_width"),
            mm20=_f(row, "mm20"),
            mm200=_f(row, "mm200"),
            mm200_daily=_f(row, "mm200_daily"),
            daily_close=_f(row, "daily_close"),
            macro_bull=bool(row["macro_bull"]) if "macro_bull" in row and row["macro_bull"] == row["macro_bull"] else None,
            prev_close=_f(row, "prev_close"),
            prev_bb_width=_f(row, "prev_bb_width"),
            ema20=_f(row, "ema20"),
            ema200=_f(row, "ema200"),
            prev_ema20=_f(row, "prev_ema20"),
            high_20=_f(row, "high_20"),
            volume_sma20=_f(row, "volume_sma20"),
            supertrend=_f(row, "supertrend"),
            supertrend_dir=_f(row, "supertrend_dir"),
            prev_supertrend_dir=_f(row, "prev_supertrend_dir"),
        )
        pos = (
            Position(
                symbol="BTC/USDT",
                side=Side.BUY,
                quantity=1.0,
                entry_price=float(row["close"]),
                entry_time=candle.timestamp,
            )
            if in_position
            else None
        )
        return strategy.evaluate(candle, indicators, pos)

    return _fn


def _f(row, col: str) -> float | None:
    val = row.get(col)
    if val is None or val != val:
        return None
    return float(val)


__all__ = [
    "BBSqueezeV1",
    "BreakoutHigh20V1",
    "MM200DailyMacroV1",
    "MM200TrendV1",
    "MM200TrendV2",
    "PortfolioMacroMicroV1",
    "PullbackEma20V1",
    "RangeHunterV1",
    "RangeHunterV2",
    "RegimeSwitchingV1",
    "SupertrendMm200V1",
    "STRATEGY_BUILDERS",
    "build_strategy_from_config",
    "get_signal_fn",
    "list_strategies",
]
