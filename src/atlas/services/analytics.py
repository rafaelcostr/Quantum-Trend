from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from atlas.research.backtester import QuickTrade, run_backtest
from atlas.research.reports import load_report_by_strategy_timeframe, load_report_for_config
from atlas.runtime.state import active_config

LABELS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _month_label(iso_ts: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return LABELS[dt.month - 1]
    except ValueError:
        return "—"


def trade_from_report_row(raw: dict) -> QuickTrade:
    raw_pct = float(raw.get("pnl_pct", 0))
    pnl_pct = raw_pct * 100 if abs(raw_pct) <= 1 else raw_pct
    return QuickTrade(
        entry_time=str(raw.get("entry_time", "")),
        exit_time=str(raw.get("exit_time") or ""),
        entry=float(raw.get("entry", raw.get("entry_price", 0))),
        exit=float(raw.get("exit", raw.get("exit_price", 0))),
        pnl=float(raw.get("pnl", 0)),
        pnl_pct=pnl_pct,
    )


def equity_curve_for_ui(report: dict | None, fallback: list[dict]) -> list[dict]:
    if report and report.get("equity_curve"):
        out: list[dict] = []
        for row in report["equity_curve"]:
            ts = str(row.get("timestamp", row.get("day", "")))
            day = ts[:10] if len(ts) >= 10 else ts or "—"
            out.append({"day": day, "equity": round(float(row.get("equity", 0)), 2)})
        return out
    return fallback


def monthly_returns_from_equity(equity_curve: list[dict]) -> list[dict]:
    """Retorno % de cada mês calendário (equity fim vs início do mês)."""
    if not equity_curve:
        return []
    by_month: dict[str, list[float]] = defaultdict(list)
    for row in equity_curve:
        ts = str(row.get("timestamp", row.get("day", "")))
        if len(ts) < 7:
            continue
        ym = ts[:7]
        by_month[ym].append(float(row.get("equity", 0)))

    out: list[dict] = []
    prev_end: float | None = None
    for ym in sorted(by_month.keys()):
        points = by_month[ym]
        start = prev_end if prev_end is not None else points[0]
        end = points[-1]
        if not start:
            continue
        ret_pct = ((end / start) - 1) * 100
        year, month_num = ym.split("-")
        label = f"{LABELS[int(month_num) - 1]}/{year[2:]}"
        out.append({"m": label, "r": round(ret_pct, 1), "ym": ym})
        prev_end = end
    return out


def monthly_returns_from_trades(trades: list[QuickTrade], initial: float = 10000) -> list[dict]:
    """Legado: contribuição dos trades por mês (não bate com retorno total composto)."""
    if not trades:
        return []
    buckets: dict[str, float] = defaultdict(float)
    equity = initial
    for t in trades:
        month = _month_label(t.exit_time)
        ret_pct = (t.pnl / equity) * 100 if equity else 0
        buckets[month] += ret_pct
        equity += t.pnl
    return [{"m": m, "r": round(v, 1)} for m, v in buckets.items()]


def trade_distribution(trades: list[QuickTrade]) -> list[dict]:
    buckets = {"<-5%": 0, "-5..-2": 0, "-2..0": 0, "0..2": 0, "2..5": 0, ">5%": 0}
    for t in trades:
        pct = t.pnl_pct
        if pct < -5:
            buckets["<-5%"] += 1
        elif pct < -2:
            buckets["-5..-2"] += 1
        elif pct < 0:
            buckets["-2..0"] += 1
        elif pct < 2:
            buckets["0..2"] += 1
        elif pct < 5:
            buckets["2..5"] += 1
        else:
            buckets[">5%"] += 1
    return [{"bucket": k, "n": v} for k, v in buckets.items()]


def load_trades_for_results(
    *,
    strategy: str | None = None,
    timeframe: str | None = None,
    quote: str = "USDT",
) -> tuple[dict, list[QuickTrade], list[dict]]:
    cfg = active_config()
    strategy = strategy or cfg.strategy.name
    timeframe = (timeframe or cfg.exchange.timeframe).lower()

    report = load_report_by_strategy_timeframe(strategy, timeframe, quote=quote)
    if report:
        metrics = report["metrics"]
        trades = [trade_from_report_row(t) for t in report.get("trades", [])]
        equity = equity_curve_for_ui(report, [])
        if equity:
            return metrics, trades, equity

    if strategy == cfg.strategy.name and timeframe == cfg.exchange.timeframe.lower():
        report = load_report_for_config(cfg)
        if report:
            metrics = report["metrics"]
            trades = [trade_from_report_row(t) for t in report.get("trades", [])]
            equity = equity_curve_for_ui(report, [])
            if equity:
                return metrics, trades, equity

        m, trades, eq_df = run_backtest(cfg)
        metrics = m.model_dump()
        equity = eq_df.to_dict(orient="records")
        return metrics, trades, equity

    raise FileNotFoundError(f"Relatório de backtest não encontrado para {strategy} · {timeframe}")


def extended_summary(metrics: dict) -> list[list[str]]:
    sharpe = float(metrics.get("sharpe", 0))
    dd = float(metrics.get("max_drawdown_pct", 0))
    return [
        ["Retorno total", f"{metrics.get('total_return_pct', 0):+.1f}%", "text-success"],
        ["Sharpe", f"{sharpe:.2f}", "text-secondary"],
        ["Calmar", f"{(float(metrics.get('total_return_pct', 0)) / max(dd, 0.1)):.2f}", "text-warning"],
        ["Win Rate", f"{metrics.get('win_rate_pct', 0):.1f}%", "text-success"],
        ["Profit Factor", f"{metrics.get('profit_factor', 0):.2f}", "text-primary"],
        ["Max DD", f"-{dd:.1f}%", "text-destructive"],
        ["Trades", str(metrics.get("trades", 0)), "text-secondary"],
    ]
