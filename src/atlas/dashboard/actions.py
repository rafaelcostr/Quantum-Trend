from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Any

from atlas.brokers.binance import BinanceDemoBroker
from atlas.core.config import AtlasConfig, load_config
from atlas.core.models import TradingMode
from atlas.intelligence.analyzer import analyze_path
from atlas.intelligence.compare_report import export_all_reports
from atlas.intelligence.metrics import discover_reports
from atlas.intelligence.research_store import save_walkforward
from atlas.research.backtester import run_backtest as run_backtest_engine
from atlas.research.collector import cache_path, load_or_download, save_candles_to_db
from atlas.core.symbols import quote_from_symbol, report_name_stem
from atlas.research.statistics import compute_buy_hold_return, compute_statistics, save_report
from atlas.research.walkforward import run_walk_forward
from atlas.runtime.runner import TradingRunner


def list_config_files(project_root: Path, pattern: str = "backtest*.yaml") -> list[Path]:
    return sorted((project_root / "config").glob(pattern))


def _apply_research_options(
    config: AtlasConfig,
    *,
    timeframe: str | None = None,
    quote: str | None = None,
) -> AtlasConfig:
    cfg = config.model_copy(deep=True)
    if timeframe:
        cfg.exchange.timeframe = timeframe.lower()
    if quote:
        cfg.exchange.symbol = f"BTC/{quote.upper()}"
    return cfg


def run_download(
    project_root: Path,
    config_rel: str,
    *,
    force: bool = False,
    to_db: bool = False,
    timeframe: str | None = None,
    quote: str | None = None,
) -> dict[str, Any]:
    config = _apply_research_options(
        load_config(project_root / config_rel),
        timeframe=timeframe,
        quote=quote,
    )
    cache_file = project_root / cache_path(config)
    had_cache = cache_file.is_file()
    df = load_or_download(config, force=force)
    result: dict[str, Any] = {
        "ok": True,
        "candles": len(df),
        "symbol": config.exchange.symbol,
        "timeframe": config.exchange.timeframe,
        "cache_dir": str(config.data.cache_dir),
        "cache_file": str(cache_file),
        "from_cache": had_cache and not force,
        "re_downloaded": force or not had_cache,
    }
    if to_db:
        count = save_candles_to_db(config, df)
        result["db_rows"] = count
    return result


def run_backtest_dashboard(
    project_root: Path,
    config_rel: str,
    output_dir: str = "data/reports",
    *,
    timeframe: str | None = None,
    quote: str | None = None,
) -> dict[str, Any]:
    """Executa backtest a partir de um YAML (dashboard/CLI helper)."""
    config = _apply_research_options(
        load_config(project_root / config_rel),
        timeframe=timeframe,
        quote=quote,
    )
    return run_backtest_config(
        project_root,
        config,
        output_dir=output_dir,
        config_file=config_rel,
    )


# Alias legado — evita quebrar imports antigos
run_backtest = run_backtest_dashboard


def run_backtest_config(
    project_root: Path,
    config: AtlasConfig,
    output_dir: str = "data/reports",
    *,
    config_file: str | None = None,
) -> dict[str, Any]:
    df = load_or_download(config)
    if df.empty:
        return {"ok": False, "error": "Sem dados. Baixe os candles primeiro."}

    result_bt = run_backtest_engine(config, df)
    report = compute_statistics(result_bt)
    warmup = int(config.strategy.params.get("warmup_bars", 205))
    bh_return = compute_buy_hold_return(df, warmup, config.risk.initial_capital)
    quote = quote_from_symbol(config.exchange.symbol)
    report_name = report_name_stem(config.strategy.name, config.exchange.timeframe, quote)
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


def run_backtest_all(
    project_root: Path,
    output_dir: str = "data/reports",
    *,
    timeframe: str | None = None,
    quote: str | None = None,
) -> dict[str, Any]:
    """Roda backtest separado para cada config/backtest*.yaml."""
    configs = list_config_files(project_root)
    if not configs:
        return {"ok": False, "error": "Nenhum config/backtest*.yaml encontrado."}

    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for cfg_path in configs:
        rel = f"config/{cfg_path.name}"
        res = run_backtest_dashboard(
            project_root,
            rel,
            output_dir=output_dir,
            timeframe=timeframe,
            quote=quote,
        )
        if res.get("ok"):
            rows.append(
                {
                    "Config": cfg_path.name,
                    "Estrategia": res["strategy"],
                    "Timeframe": res.get("timeframe", timeframe or "4h"),
                    "Par": res.get("symbol", ""),
                    "Retorno": res["net_profit_pct"],
                    "PF": res["profit_factor"],
                    "Max DD": res["max_drawdown_pct"],
                    "Trades": res["total_trades"],
                    "Sharpe": res.get("sharpe_ratio"),
                    "Relatorio": res["report_path"],
                }
            )
        else:
            errors.append(f"{cfg_path.name}: {res.get('error', 'falha')}")

    rows.sort(key=lambda r: r.get("Retorno") or 0, reverse=True)
    return {
        "ok": True,
        "rows": rows,
        "total": len(configs),
        "ok_count": len(rows),
        "errors": errors,
    }


def run_compare(project_root: Path, reports_dir: str = "data/reports", top: int = 20) -> dict[str, Any]:
    report_paths = discover_reports(project_root / reports_dir)
    if not report_paths:
        return {"ok": False, "error": "Nenhum relatorio. Rode um backtest primeiro."}

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


def run_comparison_report(
    project_root: Path,
    reports_dir: str = "data/reports",
    *,
    include_full: bool = True,
) -> dict[str, Any]:
    """Gera Markdown comparando todos os backtests e salva em disco."""
    return run_export_all_reports(project_root, reports_dir=reports_dir, include_full=include_full)


def run_export_all_reports(
    project_root: Path,
    reports_dir: str = "data/reports",
    *,
    include_full: bool = True,
) -> dict[str, Any]:
    """Comparativo + cada relatorio .md + ZIP."""
    out_dir = project_root / reports_dir
    return export_all_reports(out_dir, include_full_consolidated=include_full)


def run_walkforward(
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

    config = _apply_research_options(
        load_config(project_root / config_rel),
        timeframe=timeframe,
        quote=quote,
    )
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
    }


def run_trade_check(
    project_root: Path,
    config_rel: str,
    *,
    ops_config: AtlasConfig | None = None,
) -> dict[str, Any]:
    config = ops_config or load_config(project_root / config_rel)
    key = os.getenv("BINANCE_DEMO_API_KEY", "").strip()
    secret = os.getenv("BINANCE_DEMO_API_SECRET", "").strip()
    env_file = project_root / ".env"

    result: dict[str, Any] = {
        "env_file": env_file.is_file(),
        "api_key_ok": bool(key),
        "secret_ok": bool(secret),
        "api_key_len": len(key),
    }

    if not key or not secret:
        result["ok"] = False
        result["error"] = "Preencha BINANCE_DEMO_API_KEY e BINANCE_DEMO_API_SECRET no .env"
        return result

    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as resp:
            result["public_ip"] = resp.read().decode().strip()
    except Exception:
        result["public_ip"] = None

    broker = BinanceDemoBroker(config.exchange.symbol)
    diag = broker.check_connection()
    result.update(diag)
    result["symbol"] = config.exchange.symbol
    quote = config.exchange.symbol.split("/")[-1].upper()
    if diag.get("quote_free") is not None:
        result["quote_free"] = f"${float(diag['quote_free']):,.2f} ({quote})"
    result["ok"] = str(diag.get("balance", "")) == "ok"
    if not result["ok"]:
        result["error"] = "Conexao Binance Demo falhou (erro -2015 = chave/IP/permissao)"
    return result


def run_paper_once(config: AtlasConfig) -> dict[str, Any]:
    if config.mode != TradingMode.PAPER:
        return {"ok": False, "error": "Config deve ser mode: paper"}
    try:
        runner = TradingRunner(config)
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}

    warning = runner.engine.journal.fallback_message
    try:
        outcome = runner.tick()
    except Exception as exc:
        return {"ok": False, "error": str(exc), "warning": warning}

    return {"ok": True, "outcome": outcome, "warning": warning}
