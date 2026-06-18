from __future__ import annotations

import numpy as np
import pandas as pd


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1 / period, adjust=False).mean()


def add_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    close_col: str = "close",
) -> pd.DataFrame:
    mid = df[close_col].rolling(period).mean()
    std = df[close_col].rolling(period).std()
    df["bb_mid"] = mid
    df["bb_upper"] = mid + std_dev * std
    df["bb_lower"] = mid - std_dev * std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]
    return df


def add_rsi(df: pd.DataFrame, period: int = 14, close_col: str = "close") -> pd.DataFrame:
    delta = df[close_col].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = _wilder_smooth(gain, period)
    avg_loss = _wilder_smooth(loss, period)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = _wilder_smooth(tr, period)
    return df


def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = _wilder_smooth(tr, period)
    plus_di = 100 * _wilder_smooth(pd.Series(plus_dm, index=df.index), period) / atr
    minus_di = 100 * _wilder_smooth(pd.Series(minus_dm, index=df.index), period) / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    df["adx"] = _wilder_smooth(dx, period)
    return df


def detect_support_resistance(
    df: pd.DataFrame,
    lookback: int = 100,
    touch_pct: float = 0.01,
) -> pd.DataFrame:
    supports = []
    resistances = []
    lows = df["low"].values
    highs = df["high"].values
    closes = df["close"].values
    for i in range(len(df)):
        start = max(0, i - lookback + 1)
        window_low = lows[start : i + 1]
        window_high = highs[start : i + 1]
        support = float(np.min(window_low))
        resistance = float(np.max(window_high))
        price = closes[i]
        if price > 0 and abs(price - support) / price <= touch_pct:
            supports.append(support)
        else:
            supports.append(np.nan)
        if price > 0 and abs(price - resistance) / price <= touch_pct:
            resistances.append(resistance)
        else:
            resistances.append(np.nan)
    df["support"] = supports
    df["resistance"] = resistances
    return df


def add_moving_averages(
    df: pd.DataFrame,
    periods: list[int] | None = None,
    close_col: str = "close",
) -> pd.DataFrame:
    for period in periods or [20, 200]:
        df[f"mm{period}"] = df[close_col].rolling(period).mean()
    df["ma_fast"] = df.get(f"mm{(periods or [20, 200])[0]}")
    df["ma_slow"] = df.get(f"mm{(periods or [20, 200])[-1]}")
    return df


def add_ema(
    df: pd.DataFrame,
    periods: list[int] | None = None,
    close_col: str = "close",
) -> pd.DataFrame:
    for period in periods or [20, 200]:
        df[f"ema{period}"] = df[close_col].ewm(span=period, adjust=False).mean()
    if 20 in (periods or [20, 200]):
        df["prev_ema20"] = df["ema20"].shift(1)
    return df


def add_breakout_levels(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
    df["high_20"] = df["high"].rolling(lookback).max().shift(1)
    df["low_20"] = df["low"].rolling(lookback).min().shift(1)
    if "volume" in df.columns:
        df["volume_sma20"] = df["volume"].rolling(lookback).mean()
    return df


def add_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
    if "atr" not in df.columns:
        df = add_atr(df, period)
    atr = df["atr"]
    hl2 = (df["high"] + df["low"]) / 2
    basic_ub = hl2 + multiplier * atr
    basic_lb = hl2 - multiplier * atr

    final_ub = np.full(len(df), np.nan)
    final_lb = np.full(len(df), np.nan)
    st = np.full(len(df), np.nan)
    direction = np.ones(len(df))

    close = df["close"].values
    bu = basic_ub.values
    bl = basic_lb.values

    for i in range(len(df)):
        if np.isnan(bu[i]) or np.isnan(bl[i]):
            continue
        if i == 0:
            final_ub[i] = bu[i]
            final_lb[i] = bl[i]
        else:
            final_ub[i] = bu[i] if (bu[i] < final_ub[i - 1] or close[i - 1] > final_ub[i - 1]) else final_ub[i - 1]
            final_lb[i] = bl[i] if (bl[i] > final_lb[i - 1] or close[i - 1] < final_lb[i - 1]) else final_lb[i - 1]

        if i == 0:
            direction[i] = 1
        elif direction[i - 1] == 1:
            direction[i] = -1 if close[i] < final_lb[i] else 1
        else:
            direction[i] = 1 if close[i] > final_ub[i] else -1

        st[i] = final_lb[i] if direction[i] == 1 else final_ub[i]

    df["supertrend"] = st
    df["supertrend_dir"] = direction
    df["prev_supertrend_dir"] = pd.Series(direction).shift(1)
    return df


def add_daily_macro(df: pd.DataFrame, mm_period: int = 200) -> pd.DataFrame:
    daily = df.resample("1D").agg({"close": "last", "open": "first", "high": "max", "low": "min"})
    daily = daily.dropna(subset=["close"])
    daily["mm200_daily"] = daily["close"].rolling(mm_period).mean()
    daily["macro_bull"] = (daily["close"].shift(1) > daily["mm200_daily"].shift(1)).astype(float)
    df["mm200_daily"] = daily["mm200_daily"].shift(1).reindex(df.index, method="ffill")
    df["daily_close"] = daily["close"].shift(1).reindex(df.index, method="ffill")
    df["macro_bull"] = daily["macro_bull"].reindex(df.index, method="ffill")
    return df


def add_indicators(
    df: pd.DataFrame,
    bb_period: int = 20,
    bb_std: float = 2.0,
    rsi_period: int = 14,
    adx_period: int = 14,
    sr_lookback: int = 100,
    sr_touch_pct: float = 0.01,
    mm_periods: list[int] | None = None,
    include_daily_macro: bool = False,
    daily_mm_period: int = 200,
    ema_periods: list[int] | None = None,
    breakout_lookback: int = 20,
    supertrend_period: int = 10,
    supertrend_mult: float = 3.0,
) -> pd.DataFrame:
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        if "timestamp" in out.columns:
            out = out.set_index("timestamp")
    out = add_bollinger_bands(out, period=bb_period, std_dev=bb_std)
    out = add_rsi(out, period=rsi_period)
    out = add_atr(out, period=14)
    out = add_adx(out, period=adx_period)
    out = add_moving_averages(out, periods=mm_periods or [20, 200])
    out = add_ema(out, periods=ema_periods or [20, 200])
    out = add_breakout_levels(out, lookback=breakout_lookback)
    out = add_supertrend(out, period=supertrend_period, multiplier=supertrend_mult)
    out = detect_support_resistance(out, lookback=sr_lookback, touch_pct=sr_touch_pct)
    if include_daily_macro:
        out = add_daily_macro(out, mm_period=daily_mm_period)
    out["prev_close"] = out["close"].shift(1)
    out["prev_bb_width"] = out["bb_width"].shift(1)
    return out


def add_indicators_from_params(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    mm20 = int(params.get("mm20_period", params.get("ema_fast", params.get("ma_fast", 20))))
    mm200 = int(params.get("mm200_period", params.get("ema_slow", params.get("ma_period", params.get("ma_slow", 200)))))
    ema_periods = params.get("ema_periods_override")
    if ema_periods is None:
        ema_fast = int(params.get("ema_fast", mm20))
        ema_mid = int(params.get("ema_mid", 50))
        ema_slow = int(params.get("ema_slow", mm200))
        ema_periods = sorted(set([ema_fast, ema_mid, ema_slow]))
    return add_indicators(
        df,
        bb_period=int(params.get("bb_period", 20)),
        bb_std=float(params.get("bb_std", 2.0)),
        rsi_period=int(params.get("rsi_period", 14)),
        adx_period=int(params.get("adx_period", 14)),
        sr_lookback=int(params.get("sr_lookback", 100)),
        sr_touch_pct=float(params.get("sr_touch_pct", 0.01)),
        mm_periods=[mm20, mm200],
        include_daily_macro=bool(params.get("include_daily_macro", False)),
        daily_mm_period=int(params.get("daily_mm_period", 200)),
        ema_periods=[int(p) for p in ema_periods],
        breakout_lookback=int(params.get("breakout_lookback", params.get("high_lookback", 20))),
        supertrend_period=int(params.get("supertrend_period", params.get("st_period", 10))),
        supertrend_mult=float(params.get("supertrend_mult", params.get("st_mult", 3.0))),
    )


def row_to_indicator_snapshot(row: pd.Series) -> dict:
    def _get(col: str) -> float | None:
        val = row.get(col)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        return float(val)

    result = {
        "bb_upper": _get("bb_upper"),
        "bb_mid": _get("bb_mid"),
        "bb_lower": _get("bb_lower"),
        "rsi": _get("rsi"),
        "adx": _get("adx"),
        "atr": _get("atr"),
        "support": _get("support"),
        "resistance": _get("resistance"),
        "bb_width": _get("bb_width"),
        "mm20": _get("mm20"),
        "mm200": _get("mm200"),
        "mm200_daily": _get("mm200_daily"),
        "daily_close": _get("daily_close"),
        "prev_close": _get("prev_close"),
        "prev_bb_width": _get("prev_bb_width"),
        "ema20": _get("ema20"),
        "ema50": _get("ema50"),
        "ema200": _get("ema200"),
        "prev_ema20": _get("prev_ema20"),
        "high_20": _get("high_20"),
        "low_20": _get("low_20"),
        "volume_sma20": _get("volume_sma20"),
        "supertrend": _get("supertrend"),
        "supertrend_dir": _get("supertrend_dir"),
        "prev_supertrend_dir": _get("prev_supertrend_dir"),
    }
    mb = row.get("macro_bull")
    if mb is not None and not (isinstance(mb, float) and np.isnan(mb)):
        result["macro_bull"] = bool(mb >= 1.0)
    return result
