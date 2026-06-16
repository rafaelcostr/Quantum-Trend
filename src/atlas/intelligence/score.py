from __future__ import annotations

from atlas.intelligence.glossary import (
    metric_reading,
    status_drawdown,
    status_expectancy,
    status_profit_factor,
    status_return,
    status_sharpe,
    status_trades,
)
from atlas.intelligence.metrics import ReportBundle, compute_expectancy, infer_initial_capital
from atlas.intelligence.models import MetricReading


def score_label(score: float) -> tuple[str, str]:
    if score >= 90:
        return "Excelente", "🟢"
    if score >= 80:
        return "Muito Bom", "🟢"
    if score >= 70:
        return "Promissor", "🟡"
    if score >= 60:
        return "Precisa Melhorar", "🟠"
    return "Rejeitado", "🔴"


def _subscore_pf(pf: float) -> float:
    if pf >= 2.0:
        return 100
    if pf >= 1.5:
        return 88
    if pf >= 1.3:
        return 75
    if pf >= 1.2:
        return 65
    if pf >= 1.0:
        return 45
    return 20


def _subscore_dd(dd: float) -> float:
    if dd <= 0.10:
        return 95
    if dd <= 0.15:
        return 85
    if dd <= 0.20:
        return 75
    if dd <= 0.25:
        return 60
    if dd <= 0.30:
        return 45
    return max(10, 35 - (dd - 0.30) * 80)


def _subscore_sharpe(sharpe: float | None) -> float:
    if sharpe is None:
        return 40
    if sharpe >= 1.5:
        return 95
    if sharpe >= 1.0:
        return 80
    if sharpe >= 0.7:
        return 65
    if sharpe >= 0.5:
        return 50
    return 30


def _subscore_expectancy(exp: float) -> float:
    if exp >= 0.02:
        return 95
    if exp >= 0.01:
        return 80
    if exp >= 0.005:
        return 65
    if exp >= 0:
        return 45
    return 15


def _subscore_return(ret: float) -> float:
    if ret >= 1.0:
        return 95
    if ret >= 0.5:
        return 85
    if ret >= 0.2:
        return 70
    if ret >= 0:
        return 50
    return 20


def _subscore_trades(n: int) -> float:
    if n >= 100:
        return 100
    if n >= 50:
        return 85
    if n >= 30:
        return 70
    if n >= 20:
        return 50
    return 25


def compute_atlas_score(
    *,
    max_drawdown_pct: float,
    profit_factor: float,
    expectancy_pct: float,
    sharpe: float | None,
    net_profit_pct: float,
    total_trades: int,
    confidence_subscore: float,
) -> float:
    raw = (
        _subscore_dd(max_drawdown_pct) * 0.25
        + _subscore_pf(profit_factor) * 0.25
        + _subscore_expectancy(expectancy_pct) * 0.15
        + _subscore_sharpe(sharpe) * 0.15
        + _subscore_return(net_profit_pct) * 0.10
        + _subscore_trades(total_trades) * 0.05
        + confidence_subscore * 0.05
    )
    if total_trades < 30:
        raw = min(raw, 65.0)
    return round(min(100.0, max(0.0, raw)), 1)


def build_level1_metrics(bundle: ReportBundle) -> tuple[list[MetricReading], dict[str, float]]:
    stats = bundle.statistics
    initial = infer_initial_capital(stats, bundle.trades, bundle.equity_curve)
    expectancy = compute_expectancy(bundle.trades, initial)

    pf = float(stats.get("profit_factor", 0))
    dd = float(stats.get("max_drawdown_pct", 0))
    sharpe = stats.get("sharpe_ratio")
    sharpe_f = float(sharpe) if sharpe is not None else None
    ret = float(stats.get("net_profit_pct", 0))
    trades = int(stats.get("total_trades", 0))

    metrics = [
        metric_reading("profit_factor", "Profit Factor", pf, f"{pf:.2f}", status_profit_factor),
        metric_reading("drawdown", "Drawdown Máx.", dd, f"{dd:.1%}", status_drawdown),
        metric_reading("expectancy", "Expectância", expectancy, f"{expectancy:.2%}", status_expectancy),
        metric_reading("sharpe", "Sharpe Ratio", sharpe_f, f"{sharpe_f:.2f}" if sharpe_f else "N/A", status_sharpe),
        metric_reading("return", "Retorno Total", ret, f"{ret:.1%}", status_return),
        metric_reading("trades", "Nº Trades", trades, str(trades), status_trades),
    ]

    values = {
        "profit_factor": pf,
        "max_drawdown_pct": dd,
        "expectancy_pct": expectancy,
        "sharpe_ratio": sharpe_f,
        "net_profit_pct": ret,
        "total_trades": trades,
        "initial_capital": initial,
        "net_profit": float(stats.get("net_profit", 0)),
        "win_rate": float(stats.get("win_rate", 0)),
    }
    return metrics, values
