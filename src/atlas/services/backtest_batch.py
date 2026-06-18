from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from atlas.core.env import project_root
from atlas.dashboard.actions import run_backtest_dashboard
from atlas.strategies.metadata import config_file_for_strategy
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
            except (json.JSONDecodeError, OSError, TypeError, ValueError):
                pass
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
    root: Path | None = None,
) -> dict[str, Any]:
    root = root or project_root()
    config_rel = resolve_backtest_config_path(strategy, timeframe)
    result = run_backtest_dashboard(root, config_rel, timeframe=timeframe.lower(), quote=quote)
    ok = result.get("ok", True) and not result.get("error")
    item = {
        "strategy": strategy,
        "strategy_label": strategy_display_name(strategy),
        "timeframe": timeframe.lower(),
        "config_path": config_rel,
        "ok": ok,
        "report_path": result.get("report_path"),
        "error": result.get("error"),
    }
    if ok:
        item["metrics"] = metrics_from_backtest_result(result)
    return item


def run_all_strategies_backtest(
    *,
    timeframes: tuple[str, ...] = DEFAULT_TIMEFRAMES,
    quote: str = "USDT",
    root: Path | None = None,
    on_progress: Callable[[int, str], None] | None = None,
) -> dict[str, Any]:
    root = root or project_root()
    items: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    strategies = list_strategies(include_legacy=False)
    if not strategies:
        strategies = list_strategies(include_legacy=True)

    for strategy in strategies:
        for tf in timeframes:
            label = f"{strategy_display_name(strategy)} · {tf.upper()}"
            if on_progress:
                on_progress(len(items), label)
            try:
                item = run_strategy_backtest(strategy, tf, quote=quote, root=root)
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
                        "ok": False,
                        "error": str(exc),
                    }
                )

    if on_progress:
        on_progress(len(items), "Concluído")

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
        "timeframes": list(timeframes),
        "quote": quote.upper(),
        "best": best,
        "items": items,
        "errors": errors,
    }


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
    from atlas.core.symbols import parse_strategy_from_report_name
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
            if not strategy or not timeframe:
                parsed_strategy, parsed_tf, parsed_quote = parse_strategy_from_report_name(path.stem)
                strategy = strategy or parsed_strategy
                timeframe = timeframe or (parsed_tf or "")
                path_quote = path_quote or (parsed_quote or "").lower()
            if not strategy or strategy == "unknown" or not timeframe:
                continue
            if path_quote and path_quote != quote_l:
                continue

            metrics = _metrics_from_report_file(path)
            ret = float(metrics.get("total_return_pct", 0))
            items.append(
                {
                    "strategy": strategy,
                    "strategy_label": strategy_display_name(strategy),
                    "timeframe": timeframe,
                    "ok": True,
                    "report_path": str(path),
                    "result": "lucro" if ret > 0 else ("empate" if ret == 0 else "prejuizo"),
                    "metrics": metrics,
                }
            )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue

    by_return = sorted(items, key=lambda x: float(x.get("metrics", {}).get("total_return_pct", 0)), reverse=True)
    by_score = sorted(items, key=lambda x: float(x.get("metrics", {}).get("atlas_score", 0)), reverse=True)

    return {
        "total": len(items),
        "quote": quote.upper(),
        "best_return": by_return[0] if by_return else None,
        "best_score": by_score[0] if by_score else None,
        "items": by_return,
    }
