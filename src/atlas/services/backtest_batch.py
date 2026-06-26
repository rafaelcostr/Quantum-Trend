from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from atlas.core.env import project_root
from atlas.core.log import log_event
from atlas.research.report_metadata import period_from_report_path, period_from_report_raw
from atlas.dashboard.actions import run_backtest_dashboard
from atlas.strategies.metadata import (
    backtest_matrix_group_labels,
    config_file_for_strategy,
    get_market_type,
    group_backtest_matrix_items,
    list_backtest_matrix_strategies,
)
from atlas.strategies.registry import list_strategies
from atlas.strategies.mm200_trend_v2 import strategy_display_name

DEFAULT_TIMEFRAMES = ("1h", "4h", "1d")


def resolve_backtest_config_path(
    strategy: str,
    timeframe: str,
    *,
    config_path: str | None = None,
) -> str:
    tf = timeframe.lower()
    if config_path:
        return config_path
    if strategy == "quantum_trend_pro":
        return "config/backtest_quantum_trend_pro.yaml"
    if tf == "1d" and strategy == "mm200_trend_v2":
        return "config/backtest_mm200_v2_1d.yaml"
    if tf == "1d" and strategy == "mm200_daily_macro_v1":
        return "config/backtest_daily_macro_1d.yaml"
    return config_file_for_strategy(strategy)


def metrics_from_backtest_result(result: dict[str, Any]) -> dict[str, Any]:
    atlas_score = 0.0
    report_path = result.get("report_path")
    if report_path:
        path = Path(report_path)
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                atlas_score = float(raw.get("metrics", {}).get("atlas_score", 0))
            except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
                log_event(
                    10,
                    "backtest_batch.report_metrics_parse.failed",
                    module="services.backtest_batch",
                    report_path=report_path,
                    error=str(exc)[:240],
                )
    return {
        "total_return_pct": round(float(result.get("net_profit_pct", 0)) * 100, 2),
        "profit_factor": round(float(result.get("profit_factor", 0)), 2),
        "max_drawdown_pct": round(float(result.get("max_drawdown_pct", 0)) * 100, 2),
        "sharpe": round(float(result.get("sharpe_ratio", 0) or 0), 2),
        "win_rate_pct": round(float(result.get("win_rate", 0)) * 100, 2),
        "trades": int(result.get("total_trades", 0)),
        "atlas_score": round(atlas_score, 1),
    }


def run_strategy_backtest(
    strategy: str,
    timeframe: str,
    *,
    quote: str = "USDT",
    base_asset: str = "BTC",
    root: Path | None = None,
) -> dict[str, Any]:
    root = root or project_root()
    config_rel = resolve_backtest_config_path(strategy, timeframe)
    result = run_backtest_dashboard(
        root,
        config_rel,
        timeframe=timeframe.lower(),
        quote=quote,
        base_asset=base_asset,
    )
    ok = result.get("ok", True) and not result.get("error")
    item = {
        "strategy": strategy,
        "strategy_label": strategy_display_name(strategy),
        "timeframe": timeframe.lower(),
        "market_type": get_market_type(strategy),
        "config_path": config_rel,
        "ok": ok,
        "report_path": result.get("report_path"),
        "error": result.get("error"),
    }
    if ok:
        item["metrics"] = metrics_from_backtest_result(result)
        item.update(period_from_report_path(result.get("report_path")))
    item["base_asset"] = base_asset.upper()
    return item


def run_all_strategies_backtest(
    *,
    timeframes: tuple[str, ...] = DEFAULT_TIMEFRAMES,
    quote: str = "USDT",
    base_asset: str = "BTC",
    root: Path | None = None,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    root = root or project_root()
    items: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    strategies = list_backtest_matrix_strategies()
    if not strategies:
        strategies = list_strategies(include_legacy=True)
    total_runs = len(strategies) * len(timeframes)

    run_index = 0
    for strategy in strategies:
        for tf in timeframes:
            run_index += 1
            label = f"{base_asset.upper()} · {strategy_display_name(strategy)} · {tf.upper()}"
            if on_progress:
                on_progress(len(items), total_runs, label)
            try:
                item = run_strategy_backtest(
                    strategy,
                    tf,
                    quote=quote,
                    base_asset=base_asset,
                    root=root,
                )
                items.append(item)
                if not item.get("ok"):
                    errors.append(
                        {
                            "strategy": strategy,
                            "timeframe": tf,
                            "error": str(item.get("error") or "Backtest falhou"),
                        }
                    )
            except Exception as exc:
                errors.append({"strategy": strategy, "timeframe": tf, "error": str(exc)})
                items.append(
                    {
                        "strategy": strategy,
                        "strategy_label": strategy_display_name(strategy),
                        "timeframe": tf.lower(),
                        "market_type": get_market_type(strategy),
                        "base_asset": base_asset.upper(),
                        "ok": False,
                        "error": str(exc),
                    }
                )

    if on_progress:
        on_progress(len(items), total_runs, "Concluído")

    passed = [i for i in items if i.get("ok")]
    ranked = sorted(
        passed,
        key=lambda x: float(x.get("metrics", {}).get("atlas_score", 0)),
        reverse=True,
    )
    best = ranked[0] if ranked else None

    return {
        "total_runs": len(items),
        "completed": len(passed),
        "failed": len(errors),
        "strategy_count": len(strategies),
        "timeframes": list(timeframes),
        "quote": quote.upper(),
        "base_asset": base_asset.upper(),
        "best": best,
        "items": items,
        "groups": _matrix_groups_payload(passed),
        "errors": errors,
    }


def _matrix_groups_payload(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = backtest_matrix_group_labels()
    grouped = group_backtest_matrix_items(items)
    out: list[dict[str, Any]] = []
    for market_type in ("bull", "bear", "range"):
        rows = sorted(
            grouped.get(market_type, []),
            key=lambda x: float(x.get("metrics", {}).get("total_return_pct", 0)),
            reverse=True,
        )
        out.append(
            {
                "market_type": market_type,
                "label": labels[market_type],
                "total": len(rows),
                "best_return": rows[0] if rows else None,
                "items": rows,
            }
        )
    return out


def _metrics_from_report_file(path: Path) -> dict[str, Any]:
    from atlas.research.reports import _normalize_report

    raw = json.loads(path.read_text(encoding="utf-8"))
    normalized = _normalize_report(raw)
    metrics = dict(normalized.get("metrics") or {})
    raw_metrics = raw.get("metrics") or {}
    if raw_metrics.get("atlas_score"):
        metrics["atlas_score"] = round(float(raw_metrics["atlas_score"]), 1)
    return metrics


def load_backtest_matrix_from_reports(*, quote: str = "USDT") -> dict[str, Any]:
    """Comparativo de todos os relatórios salvos (após testar todas ou individuais)."""
    from atlas.core.symbols import base_from_symbol, parse_strategy_from_report_name
    from atlas.intelligence.metrics import discover_reports

    reports_dir = project_root() / "data" / "reports"
    items: list[dict[str, Any]] = []
    quote_l = quote.lower()

    for path in discover_reports(reports_dir):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            meta = raw.get("metadata") or {}
            strategy = str(meta.get("strategy") or "")
            timeframe = str(meta.get("timeframe") or "").lower()
            path_quote = str(meta.get("quote") or "").lower()
            report_base = None
            if not strategy or not timeframe:
                parsed_strategy, parsed_tf, parsed_quote, parsed_base = parse_strategy_from_report_name(path.stem)
                strategy = strategy or parsed_strategy
                timeframe = timeframe or (parsed_tf or "")
                path_quote = path_quote or (parsed_quote or "").lower()
                report_base = parsed_base
            elif meta.get("market"):
                report_base = base_from_symbol(str(meta.get("market")))
            if not strategy or strategy == "unknown" or not timeframe:
                continue
            if path_quote and path_quote != quote_l:
                continue

            market = str(meta.get("market") or "")
            base_asset = str(meta.get("base_asset") or report_base or (base_from_symbol(market) if market else "BTC")).upper()

            metrics = _metrics_from_report_file(path)
            ret = float(metrics.get("total_return_pct", 0))
            period = period_from_report_raw(raw)
            items.append(
                {
                    "strategy": strategy,
                    "strategy_label": strategy_display_name(strategy),
                    "timeframe": timeframe,
                    "market_type": get_market_type(strategy),
                    "base_asset": base_asset,
                    "ok": True,
                    "report_path": str(path),
                    "result": "lucro" if ret > 0 else ("empate" if ret == 0 else "prejuizo"),
                    "metrics": metrics,
                    **period,
                }
            )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue

    by_return = sorted(items, key=lambda x: float(x.get("metrics", {}).get("total_return_pct", 0)), reverse=True)
    by_score = sorted(items, key=lambda x: float(x.get("metrics", {}).get("atlas_score", 0)), reverse=True)

    by_asset: dict[str, list[dict[str, Any]]] = {"BTC": [], "ETH": []}
    for item in by_return:
        asset = str(item.get("base_asset") or "BTC").upper()
        if asset not in by_asset:
            by_asset[asset] = []
        by_asset[asset].append(item)

    asset_payload: dict[str, Any] = {}
    for asset, rows in by_asset.items():
        sorted_rows = sorted(rows, key=lambda x: float(x.get("metrics", {}).get("total_return_pct", 0)), reverse=True)
        by_score_asset = sorted(rows, key=lambda x: float(x.get("metrics", {}).get("atlas_score", 0)), reverse=True)
        asset_payload[asset] = {
            "total": len(sorted_rows),
            "best_return": sorted_rows[0] if sorted_rows else None,
            "best_score": by_score_asset[0] if by_score_asset else None,
            "items": sorted_rows,
            "groups": _matrix_groups_payload(sorted_rows),
        }

    return {
        "total": len(items),
        "quote": quote.upper(),
        "best_return": by_return[0] if by_return else None,
        "best_score": by_score[0] if by_score else None,
        "items": by_return,
        "groups": _matrix_groups_payload(by_return),
        "by_asset": asset_payload,
    }
