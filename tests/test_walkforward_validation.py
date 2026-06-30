from __future__ import annotations

import pandas as pd

from atlas.core.config import load_config
from atlas.research.walkforward import run_walk_forward, walk_forward_to_dict


def _trend_ohlcv(n: int = 520) -> pd.DataFrame:
    idx = pd.date_range("2022-01-01", periods=n, freq="4h", tz="UTC")
    close = [100.0 + i * 0.25 + ((i % 21) - 10) * 0.08 for i in range(n)]
    return pd.DataFrame(
        {
            "open": [c - 0.2 for c in close],
            "high": [c + 0.8 for c in close],
            "low": [c - 0.8 for c in close],
            "close": close,
            "volume": [1000.0 + (i % 13) * 10 for i in range(n)],
        },
        index=idx,
    )


def test_walkforward_builds_statistical_validation_payload(tmp_path):
    config_path = tmp_path / "backtest.yaml"
    config_path.write_text(
        """
mode: backtest
exchange:
 symbol: BTC/USDT
 timeframe: 4h
strategy:
 name: pullback_ema20_v1
 params:
  ema_period: 20
  rsi_period: 14
  adx_period: 14
  warmup_bars: 80
risk:
 initial_capital: 10000
execution:
 fee_rate: 0.001
 slippage_rate: 0.0005
""",
        encoding="utf-8",
    )
    wf = run_walk_forward(load_config(config_path), _trend_ohlcv(), train_pct=0.65)
    payload = walk_forward_to_dict(wf)

    assert payload["in_sample"]
    assert payload["out_of_sample"]
    assert payload["holdout"] is not None
    assert isinstance(payload["rolling_windows"], list)
    assert payload["monte_carlo"]
    assert "score" in payload["robustness"]
    assert any(item["label"] == "Walk-forward aprovado" for item in payload["promotion_checklist"])
