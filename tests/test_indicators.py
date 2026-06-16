import pandas as pd
import pytest

from atlas.core.indicators import add_indicators


def test_add_indicators_columns():
    n = 250
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": range(n),
            "high": range(1, n + 1),
            "low": range(n),
            "close": range(n),
            "volume": [1000.0] * n,
        },
        index=idx,
    )
    result = add_indicators(df)
    for col in ("bb_upper", "bb_mid", "bb_lower", "rsi", "adx", "atr"):
        assert col in result.columns
    assert result["bb_upper"].iloc[-1] > result["bb_mid"].iloc[-1]
