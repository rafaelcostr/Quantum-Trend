from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from atlas.core.config import AtlasConfig
from atlas.core.symbols import quote_from_symbol
from atlas.research.engine_backtest import BacktestResult
from atlas.research.report_metadata import build_report_metadata, remove_stale_reports


@dataclass
class PerformanceReport:
    net_profit: float
    net_profit_pct: float
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    best_trade_pct: float
    worst_trade_pct: float
    avg_trade_pct: float
    sharpe_ratio: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _max_drawdown(equity: list[float]) -> float:
    if not equity:
        return 0.0
    peak = equity[0]
    max_dd = 0.0
    for val in equity:
        peak = max(peak, val)
        if peak > 0:
            max_dd = max(max_dd, (peak - val) / peak)
    return max_dd


def compute_statistics(result: BacktestResult) -> PerformanceReport:
    trades = result.trades
    initial = result.initial_capital
    final = result.final_equity
    net_profit = final - initial
    net_profit_pct = net_profit / initial if initial else 0.0

    if not trades:
        equity_vals = [e for _, e in result.equity_curve]
        return PerformanceReport(
            net_profit=net_profit,
            net_profit_pct=net_profit_pct,
            total_trades=0,
            win_rate=0.0,
            profit_factor=0.0,
            max_drawdown_pct=_max_drawdown(equity_vals),
            best_trade_pct=0.0,
            worst_trade_pct=0.0,
            avg_trade_pct=0.0,
            sharpe_ratio=None,
        )

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    pnls_pct = [t.pnl_pct for t in trades]
    equity_vals = [e for _, e in result.equity_curve]

    sharpe = None
    if len(equity_vals) > 2:
        returns = np.diff(equity_vals) / np.array(equity_vals[:-1])
        returns = returns[np.isfinite(returns)]
        if len(returns) > 1 and returns.std() > 0:
            sharpe = float((returns.mean() / returns.std()) * np.sqrt(365 * 6))

    return PerformanceReport(
        net_profit=net_profit,
        net_profit_pct=net_profit_pct,
        total_trades=len(trades),
        win_rate=len(wins) / len(trades),
        profit_factor=pf,
        max_drawdown_pct=_max_drawdown(equity_vals),
        best_trade_pct=max(pnls_pct),
        worst_trade_pct=min(pnls_pct),
        avg_trade_pct=float(np.mean(pnls_pct)),
        sharpe_ratio=sharpe,
    )


def compute_buy_hold_return(df, warmup: int, initial_capital: float) -> float:
    if len(df) <= warmup:
        return 0.0
    start = float(df["close"].iloc[warmup])
    end = float(df["close"].iloc[-1])
    if start <= 0:
        return 0.0
    return (end / start) - 1.0


def save_report(
    result: BacktestResult,
    report: PerformanceReport,
    out_dir: Path,
    name: str = "backtest_report",
    *,
    config: AtlasConfig | None = None,
    config_file: str | None = None,
    buy_hold_pct: float | None = None,
) -> Path:
    from atlas.core.symbols import parse_strategy_from_report_name

    out_dir.mkdir(parents=True, exist_ok=True)
    strategy_name = timeframe = quote = None
    if config is not None:
        strategy_name = config.strategy.name
        timeframe = config.exchange.timeframe
        quote = quote_from_symbol(config.exchange.symbol)
    else:
        strategy_name, timeframe, quote = parse_strategy_from_report_name(name)
        quote = quote or "USDT"

    if strategy_name and timeframe and quote and strategy_name != "unknown":
        remove_stale_reports(out_dir, strategy=strategy_name, timeframe=timeframe, quote=quote)

    payload: dict = {
        "statistics": report.to_dict(),
        "trades": [
            {
                "entry_time": t.entry_time.isoformat(),
                "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "fees": t.fees,
                "strategy": t.strategy,
                "metadata": t.metadata,
            }
            for t in result.trades
        ],
        "equity_curve": [{"timestamp": ts.isoformat(), "equity": eq} for ts, eq in result.equity_curve],
    }
    if config is not None:
        payload["metadata"] = build_report_metadata(
            config,
            config_file=config_file,
            buy_hold_pct=buy_hold_pct,
            report_name=name,
        )
        if config.strategy.name == "quantum_trend_pro":
            from atlas.quantum.module_stats import compute_module_backtest_stats

            module_stats = compute_module_backtest_stats(result.trades)
            payload["module_stats"] = module_stats
            if payload.get("metadata"):
                payload["metadata"]["module_stats"] = module_stats
    path = out_dir / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
