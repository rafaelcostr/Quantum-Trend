from __future__ import annotations

from pathlib import Path
from typing import Any

from atlas.core.config import AtlasConfig, load_config
from atlas.core.symbols import build_symbol, quote_from_symbol, report_name_stem
from atlas.intelligence.analyzer import analyze_path
from atlas.intelligence.compare_report import export_all_reports
from atlas.intelligence.metrics import discover_reports
from atlas.intelligence.research_store import save_walkforward
from atlas.research.collector import cache_path, load_or_download
from atlas.research.engine_backtest import run_backtest_engine
from atlas.research.statistics import compute_buy_hold_return, compute_statistics, save_report
from atlas.research.walkforward import run_walk_forward


def list_config_files(project_root: Path, pattern: str = "backtest*.yaml") -> list[Path]:
    return sorted((project_root / "config").glob(pattern))


def _apply_research_options(
    config: AtlasConfig,
    *,
    timeframe: str | None = None,
    quote: str | None = None,
    base_asset: str | None = None,
) -> AtlasConfig:
    cfg = config.model_copy(deep=True)
    if timeframe:
        cfg.exchange.timeframe = timeframe.lower()
    base = (base_asset or cfg.exchange.symbol.split("/")[0]).upper()
    q = (quote or quote_from_symbol(cfg.exchange.symbol)).upper()
    cfg.exchange.symbol = build_symbol(base, q)
    return cfg


def run_download(
    project_root: Path,
    config_rel: str,
    *,
    force: bool = False,
    timeframe: str | None = None,
    quote: str | None = None,
    base_asset: str | None = None,
) -> dict[str, Any]:
    config = _apply_research_options(
        load_config(project_root / config_rel),
        timeframe=timeframe,
        quote=quote,
        base_asset=base_asset,
    )
    cache_file = project_root / cache_path(config)
    had_cache = cache_file.is_file()
    df = load_or_download(config, force=force)
    return {
        "ok": True,
        "candles": len(df),
        "symbol": config.exchange.symbol,
        "timeframe": config.exchange.timeframe,
        "cache_dir": str(config.data.cache_dir),
        "cache_file": str(cache_file),
        "from_cache": had_cache and not force,
        "re_downloaded": force or not had_cache,
    }


def run_backtest_dashboard(
    project_root: Path,
    config_rel: str,
    output_dir: str = "data/reports",
    *,
    timeframe: str | None = None,
    quote: str | None = None,
    base_asset: str | None = None,
) -> dict[str, Any]:
    config = _apply_research_options(
        load_config(project_root / config_rel),
        timeframe=timeframe,
        quote=quote,
        base_asset=base_asset,
    )
    return run_backtest_config(project_root, config, output_dir=output_dir, config_file=config_rel)


run_backtest = run_backtest_dashboard


def run_backtest_config(
    project_root: Path,
    config: AtlasConfig,
    output_dir: str = "data/reports",
    *,
    config_file: str | None = None,
) -> dict[str, Any]:
    from atlas.strategies.registry import build_strategy_from_config

    strategy = build_strategy_from_config(config.strategy.name, config.strategy.params)
    if getattr(strategy, "uses_multi_timeframe", False):
        from atlas.quantum.multi_timeframe import build_execution_dataset

        df = build_execution_dataset(config)
    else:
        df = load_or_download(config)
    if df.empty:
        return {"ok": False, "error": "Sem dados. Baixe os candles primeiro."}

    result_bt = run_backtest_engine(config, df)
    report = compute_statistics(result_bt)
    warmup = int(config.strategy.params.get("warmup_bars", 205))
    bh_return = compute_buy_hold_return(df, warmup, config.risk.initial_capital)
    quote = quote_from_symbol(config.exchange.symbol)
    base = config.exchange.symbol.split("/")[0]
    report_name = report_name_stem(config.strategy.name, config.exchange.timeframe, quote, base)
    path = save_report(
        result_bt,
        report,
        project_root / output_dir,
        name=report_name,
        config=config,
        config_file=config_file,
        buy_hold_pct=bh_return,
    )

    return {
        "ok": True,
        "strategy": config.strategy.name,
        "timeframe": config.exchange.timeframe,
        "symbol": config.exchange.symbol,
        "candles": len(df),
        "report_path": str(path),
        "net_profit": report.net_profit,
        "net_profit_pct": report.net_profit_pct,
        "buy_hold_pct": bh_return,
        "total_trades": report.total_trades,
        "win_rate": report.win_rate,
        "profit_factor": report.profit_factor,
        "max_drawdown_pct": report.max_drawdown_pct,
        "sharpe_ratio": report.sharpe_ratio,
    }


def run_compare(project_root: Path, reports_dir: str = "data/reports", top: int = 20) -> dict[str, Any]:
    report_paths = discover_reports(project_root / reports_dir)
    if not report_paths:
        return {"ok": False, "error": "Nenhum relatório. Rode um backtest primeiro."}

    rows: list[dict[str, Any]] = []
    for path in report_paths:
        try:
            a = analyze_path(path)
            raw = a.raw
            sharpe = raw.get("sharpe_ratio")
            rows.append(
                {
                    "Estrategia": a.strategy,
                    "Par": a.metadata.get("market") or a.market,
                    "Score": a.level1.atlas_score,
                    "Classificacao": a.level1.score_label,
                    "Retorno": raw["net_profit_pct"],
                    "DD": raw["max_drawdown_pct"],
                    "PF": raw["profit_factor"],
                    "Sharpe": sharpe if sharpe is not None else None,
                    "Trades": int(raw["total_trades"]),
                    "Confianca": a.level1.confidence,
                }
            )
        except Exception as exc:
            rows.append({"Estrategia": path.stem, "Score": None, "Erro": str(exc)})

    rows.sort(key=lambda r: r.get("Score") or 0, reverse=True)
    return {"ok": True, "rows": rows[:top], "total": len(rows)}


def run_export_all_reports(
    project_root: Path,
    reports_dir: str = "data/reports",
    *,
    include_full: bool = True,
) -> dict[str, Any]:
    return export_all_reports(project_root / reports_dir, include_full_consolidated=include_full)


def run_walkforward_dashboard(
    project_root: Path,
    config_rel: str,
    *,
    train_pct: float = 0.70,
    output_dir: str = "data/reports",
    timeframe: str | None = None,
    quote: str | None = None,
) -> dict[str, Any]:
    if not 0.5 <= train_pct <= 0.9:
        return {"ok": False, "error": "train_pct deve estar entre 0.5 e 0.9"}

    config = _apply_research_options(load_config(project_root / config_rel), timeframe=timeframe, quote=quote)
    df = load_or_download(config)
    if df.empty:
        return {"ok": False, "error": "Sem dados. Baixe os candles primeiro."}

    wf = run_walk_forward(config, df, train_pct=train_pct)
    path = save_walkforward(wf, project_root / output_dir)
    is_s = wf.in_sample
    oos_s = wf.out_of_sample

    return {
        "ok": True,
        "strategy": wf.strategy,
        "path": str(path),
        "split_timestamp": wf.split_timestamp,
        "is_return": is_s.net_profit_pct,
        "is_trades": wf.is_trades,
        "oos_return": oos_s.net_profit_pct,
        "oos_trades": wf.oos_trades,
        "oos_pf": oos_s.profit_factor,
        "oos_sharpe": oos_s.sharpe_ratio,
        "wfe": wf.walk_forward_efficiency,
        "holdout_return": wf.holdout.net_profit_pct if wf.holdout else None,
        "holdout_trades": wf.holdout_trades,
        "rolling_windows": len(wf.rolling_windows),
        "robustness_score": wf.robustness.get("score"),
        "robustness_approved": wf.robustness.get("approved"),
        "risk_of_ruin_pct": wf.monte_carlo.get("risk_of_ruin_pct"),
        "promotion_checklist": wf.promotion_checklist,
    }
