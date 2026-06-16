"""Dados agregados para o painel inicial."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from atlas.brokers.binance import fetch_public_candles
from atlas.core.config import AtlasConfig
from atlas.core.symbols import quote_from_symbol
from atlas.dashboard.bot_manager import tail_log
from atlas.dashboard.performance import compute_performance
from atlas.dashboard.service import DashboardService, fetch_demo_balances, load_journal_events
from atlas.dashboard.strategy_config import build_operational_config
from atlas.intelligence.metrics import discover_reports

MARKET_SYMBOLS = ("BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT")


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def load_backtest_stats(project_root: Path, config: AtlasConfig) -> dict[str, Any] | None:
    quote = quote_from_symbol(config.exchange.symbol).lower()
    tf = config.exchange.timeframe.lower()
    path = project_root / "data/reports" / f"{config.strategy.name}_{tf}_{quote}_report.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw.get("statistics") or {}
    except (json.JSONDecodeError, OSError):
        return None


def portfolio_allocations(
    balances: dict[str, float] | None,
    state,
    btc_price: float,
) -> dict[str, float]:
    if not balances and not state:
        return {}
    btc_qty = (balances or {}).get("btc_total") or (getattr(state, "btc_total", 0) if state else 0.0)
    usdt = (balances or {}).get("usdt_free", 0.0)
    usdc = (balances or {}).get("usdc_free", 0.0)
    btc_val = float(btc_qty) * float(btc_price or 0)
    alloc = {"BTC": btc_val, "USDT": float(usdt), "USDC": float(usdc)}
    return {k: v for k, v in alloc.items() if v > 1.0}


def compute_daily_pnl(events: list[dict], initial_capital: float) -> tuple[float, float]:
    today = date.today()
    today_equities: list[float] = []
    for ev in events:
        ts = _parse_ts(ev.get("ts"))
        if ts and ts.date() == today:
            eq = (ev.get("payload") or {}).get("equity")
            if eq is not None:
                today_equities.append(float(eq))
    if len(today_equities) >= 2:
        delta = today_equities[-1] - today_equities[0]
        pct = delta / initial_capital if initial_capital else 0.0
        return delta, pct
    if len(today_equities) == 1 and initial_capital:
        delta = today_equities[0] - initial_capital
        return delta, delta / initial_capital
    return 0.0, 0.0


def performance_metrics_rows(
    bt_stats: dict[str, Any] | None,
    perf,
    config: AtlasConfig,
) -> list[tuple[str, str]]:
    bt = bt_stats or {}
    ret = bt.get("net_profit_pct")
    dd = bt.get("max_drawdown_pct") or (perf.max_drawdown_pct if perf else None)
    cagr = bt.get("cagr")
    calmar = None
    if ret is not None and dd and dd > 0:
        calmar = float(ret) / float(dd)
    wins = int(bt.get("winning_trades") or 0)
    losses = int(bt.get("losing_trades") or 0)
    if not wins and not losses and bt.get("win_rate") and bt.get("total_trades"):
        total = int(bt["total_trades"])
        wins = int(total * float(bt["win_rate"]))
        losses = total - wins

    def pct(v):
        return f"{float(v):.2%}" if v is not None else "N/A"

    def num(v, d=2):
        return f"{float(v):.{d}f}" if v is not None else "N/A"

    return [
        ("Retorno Total", pct(ret)),
        ("CAGR", pct(cagr) if cagr is not None else pct(ret)),
        ("Drawdown Max", pct(dd)),
        ("Calmar Ratio", num(calmar) if calmar is not None else "N/A"),
        ("Expectancy", pct(bt.get("avg_trade_pct"))),
        ("Melhor Trade", pct(bt.get("best_trade_pct"))),
        ("Pior Trade", pct(bt.get("worst_trade_pct"))),
        ("Vitorias / Derrotas", f"{wins} / {losses}"),
        ("Trades (paper)", str(perf.trade_count) if perf else "0"),
        ("Capital Inicial", f"${config.risk.initial_capital:,.0f}"),
    ]


def compute_risk_score(
    config: AtlasConfig,
    perf,
    exposure_pct: float,
    max_dd_live: float,
) -> tuple[int, str]:
    score = 15
    dd_limit = config.risk.max_weekly_drawdown
    dd = max(max_dd_live, perf.max_drawdown_pct if perf else 0.0)
    if dd > dd_limit:
        score += 35
    elif dd > dd_limit * 0.7:
        score += 20
    if exposure_pct > 60:
        score += 25
    elif exposure_pct > 30:
        score += 12
    daily_limit = config.risk.max_daily_drawdown
    if perf and perf.net_pnl_pct < -daily_limit:
        score += 20
    score = min(100, max(0, score))
    if score < 35:
        level = "BAIXO"
    elif score < 65:
        level = "MEDIO"
    else:
        level = "ALTO"
    return score, level


def fetch_market_overview(timeframe: str = "4h") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol in MARKET_SYMBOLS:
        try:
            candles = fetch_public_candles(symbol, timeframe, limit=48)
            if len(candles) < 2:
                continue
            last = float(candles[-1].close)
            first = float(candles[0].close)
            chg = (last - first) / first if first else 0.0
            spark = [float(c.close) for c in candles[-12:]]
            rows.append(
                {
                    "ativo": symbol.split("/")[0],
                    "par": symbol,
                    "preco": last,
                    "var_24h": chg,
                    "spark": spark,
                }
            )
        except Exception:
            continue
    return rows


def load_signal_monitor_rows(project_root: Path, limit: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in discover_reports(project_root / "data/reports"):
        if path.name == "backtest_report.json":
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            meta = raw.get("metadata") or {}
            stats = raw.get("statistics") or {}
            ret = float(stats.get("net_profit_pct") or 0)
            wr = float(stats.get("win_rate") or 0)
            if ret > 0.08:
                signal = "LONG"
            elif ret < -0.02:
                signal = "SHORT"
            else:
                signal = "NEUTRO"
            strength = min(100, int(abs(ret) * 400 + wr * 40))
            rows.append(
                {
                    "par": meta.get("market", "BTC/USDT"),
                    "estrategia": meta.get("strategy", "?"),
                    "tf": str(meta.get("timeframe", "?")).upper(),
                    "sinal": signal,
                    "forca": strength,
                }
            )
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            continue
    rows.sort(key=lambda r: r["forca"], reverse=True)
    return rows[:limit]


def load_recent_trades(project_root: Path, config: AtlasConfig, limit: int = 8) -> list[dict[str, Any]]:
    service = DashboardService(config)
    try:
        trades, _ = service.fetch_demo_trades(limit=limit)
    except Exception:
        return []
    rows: list[dict[str, Any]] = []
    for t in reversed(trades[-limit:]):
        ts = t.get("timestamp")
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=timezone.utc)
            hora = dt.strftime("%H:%M:%S")
        else:
            hora = str(ts)[:8]
        side = str(t.get("side", "")).upper()
        side_pt = "COMPRA" if side == "BUY" else "VENDA"
        cost = float(t.get("cost") or 0)
        rows.append(
            {
                "hora": hora,
                "lado": side_pt,
                "par": t.get("symbol", config.exchange.symbol),
                "pnl": cost if side == "SELL" else -cost,
            }
        )
    return rows


def journal_feed(events: list[dict[str, Any]], limit: int = 8) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for ev in reversed(events[-limit:]):
        ts = ev.get("ts", "")
        if isinstance(ts, str) and len(ts) >= 16:
            t = ts[11:19]
        else:
            t = str(ts)[:8]
        event = str(ev.get("event", ""))
        payload = ev.get("payload") or {}
        detail = (
            payload.get("signal")
            or payload.get("reason")
            or payload.get("action")
            or payload.get("error")
            or ""
        )
        if payload.get("equity"):
            detail = f"{detail} | ${float(payload['equity']):,.0f}"
        rows.append((t, event.upper(), str(detail)[:80]))
    return rows


def live_snapshot(project_root: Path, config: AtlasConfig):
    quote = config.exchange.symbol.split("/")[-1].upper()
    ops = build_operational_config(
        project_root,
        strategy_name=config.strategy.name,
        quote_asset=quote,
        timeframe=config.exchange.timeframe,
    )
    balances, balance_error = fetch_demo_balances(ops)
    service = DashboardService(ops)
    try:
        ind_df = service.fetch_candles_df(limit=200)
    except Exception:
        ind_df = None
    state = service.get_live_state(ind_df=ind_df, balances=balances, balance_error=balance_error)
    events = load_journal_events(config.database_url, config.mode.value, limit=200)
    perf = compute_performance(
        events,
        initial_capital=config.risk.initial_capital,
        current_equity=state.equity_usdt,
    )
    return state, perf, events, balance_error, balances


def system_logs(lines: int = 12) -> str:
    text = tail_log(lines)
    return text if text else "(sem logs ainda)"
