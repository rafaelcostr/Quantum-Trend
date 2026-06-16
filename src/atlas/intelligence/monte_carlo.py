from __future__ import annotations

from typing import Any

import numpy as np


def monte_carlo_bootstrap(
    trades: list[dict[str, Any]],
    initial_capital: float,
    *,
    n_simulations: int = 1000,
    seed: int = 42,
) -> dict[str, float] | None:
    pnls = [float(t.get("pnl", 0)) for t in trades]
    if len(pnls) < 15:
        return None

    rng = np.random.default_rng(seed)
    returns: list[float] = []
    drawdowns: list[float] = []

    for _ in range(n_simulations):
        sample = rng.choice(pnls, size=len(pnls), replace=True)
        equity = initial_capital
        peak = equity
        max_dd = 0.0
        for pnl in sample:
            equity += pnl
            peak = max(peak, equity)
            if peak > 0:
                max_dd = max(max_dd, (peak - equity) / peak)
        returns.append((equity - initial_capital) / initial_capital)
        drawdowns.append(max_dd)

    arr_ret = np.array(returns)
    arr_dd = np.array(drawdowns)
    return {
        "mc_return_worst": float(np.percentile(arr_ret, 5)),
        "mc_return_median": float(np.median(arr_ret)),
        "mc_return_best": float(np.percentile(arr_ret, 95)),
        "mc_dd_worst": float(np.percentile(arr_dd, 95)),
        "mc_dd_median": float(np.median(arr_dd)),
        "mc_simulations": float(n_simulations),
    }


def bootstrap_confidence_mean_pnl(
    trades: list[dict[str, Any]],
    *,
    n_bootstrap: int = 2000,
    confidence: float = 0.95,
    seed: int = 42,
) -> dict[str, float] | None:
    pnls = np.array([float(t.get("pnl", 0)) for t in trades])
    if len(pnls) < 15:
        return None
    rng = np.random.default_rng(seed)
    means = [float(rng.choice(pnls, size=len(pnls), replace=True).mean()) for _ in range(n_bootstrap)]
    alpha = (1 - confidence) / 2
    return {
        "bootstrap_mean_pnl": float(np.mean(pnls)),
        "bootstrap_ci_low": float(np.percentile(means, alpha * 100)),
        "bootstrap_ci_high": float(np.percentile(means, (1 - alpha) * 100)),
        "bootstrap_confidence": confidence,
    }
