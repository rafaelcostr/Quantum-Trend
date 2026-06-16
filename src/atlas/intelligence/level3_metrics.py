from __future__ import annotations

from typing import Any

import numpy as np

from atlas.intelligence.metrics import ReportBundle, infer_initial_capital
from atlas.intelligence.monte_carlo import bootstrap_confidence_mean_pnl, monte_carlo_bootstrap


def compute_ulcer_index(equity_curve: list[dict[str, Any]]) -> float | None:
    if len(equity_curve) < 3:
        return None
    equities = np.array([float(p["equity"]) for p in equity_curve])
    peak = equities[0]
    sq_dd: list[float] = []
    for eq in equities:
        peak = max(peak, eq)
        if peak > 0:
            dd_pct = ((peak - eq) / peak) * 100
            sq_dd.append(dd_pct**2)
    if not sq_dd:
        return None
    return float(np.sqrt(np.mean(sq_dd)))


def compute_skewness_kurtosis(trades: list[dict[str, Any]]) -> tuple[float | None, float | None]:
    rets = np.array([float(t.get("pnl_pct", 0)) for t in trades])
    if len(rets) < 20:
        return None, None
    mean = rets.mean()
    std = rets.std()
    if std == 0:
        return None, None
    skew = float(np.mean(((rets - mean) / std) ** 3))
    kurt = float(np.mean(((rets - mean) / std) ** 4) - 3)
    return skew, kurt


def compute_kelly(win_rate: float, payoff_ratio: float | None) -> float | None:
    if payoff_ratio is None or payoff_ratio <= 0:
        return None
    kelly = win_rate - (1 - win_rate) / payoff_ratio
    return float(max(0.0, min(1.0, kelly)))


def build_level3_values(
    bundle: ReportBundle,
    walkforward: dict[str, Any] | None,
    payoff_ratio: float | None,
    win_rate: float,
) -> dict[str, Any]:
    initial = infer_initial_capital(bundle.statistics, bundle.trades, bundle.equity_curve)
    mc = monte_carlo_bootstrap(bundle.trades, initial)
    boot = bootstrap_confidence_mean_pnl(bundle.trades)
    ulcer = compute_ulcer_index(bundle.equity_curve)
    skew, kurt = compute_skewness_kurtosis(bundle.trades)
    kelly = compute_kelly(win_rate, payoff_ratio)

    values: dict[str, Any] = {
        "ulcer_index": ulcer,
        "skewness": skew,
        "kurtosis": kurt,
        "kelly_fraction": kelly,
    }

    if mc:
        values.update(mc)
    if boot:
        values.update(boot)

    if walkforward:
        oos = walkforward.get("out_of_sample", {})
        values["oos_return"] = oos.get("net_profit_pct")
        values["oos_sharpe"] = oos.get("sharpe_ratio")
        values["oos_profit_factor"] = oos.get("profit_factor")
        values["oos_trades"] = walkforward.get("oos_trades")
        values["walk_forward_efficiency"] = walkforward.get("walk_forward_efficiency")
        values["wf_split"] = walkforward.get("split_timestamp")
        is_stats = walkforward.get("in_sample", {})
        values["is_return"] = is_stats.get("net_profit_pct")

    return values
