"""Laboratório quantitativo: versionamento, comparação e replay de backtests."""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atlas.core.env import project_root
from atlas.research.report_metadata import metadata_from_report_path, period_from_report_raw
from atlas.strategies.metadata import (
    get_market_type,
    get_strategy_metadata,
    list_backtest_matrix_strategies,
)

LAB_STORE = "data/runtime/quant_lab.json"
ALLOWED_TAGS = ("promissor", "rejeitado", "overfit", "bom em alta", "bom em lateral")
ALLOWED_STATUSES = ("active", "archived", "experimental")


@dataclass(frozen=True)
class LabPaths:
    root: Path
    reports_dir: Path
    store_path: Path


def _paths(root: Path | None = None, reports_dir: Path | None = None, store_path: Path | None = None) -> LabPaths:
    base = root or project_root()
    return LabPaths(
        root=base,
        reports_dir=reports_dir or base / "data" / "reports",
        store_path=store_path or base / LAB_STORE,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else (default or {})
    except (OSError, json.JSONDecodeError):
        return default or {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _empty_store() -> dict[str, Any]:
    return {"annotations": {}, "strategies": {}, "updated_at": None}


def _load_store(paths: LabPaths) -> dict[str, Any]:
    data = _load_json(paths.store_path, _empty_store())
    data.setdefault("annotations", {})
    data.setdefault("strategies", {})
    return data


def _save_store(paths: LabPaths, store: dict[str, Any]) -> None:
    store["updated_at"] = _now()
    _write_json(paths.store_path, store)


def _code_version(root: Path) -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    version = res.stdout.strip()
    return version or "unknown"


def _experiment_id(path: Path, raw: dict[str, Any], meta: dict[str, Any]) -> str:
    seed = "|".join(
        [
            path.name,
            str(meta.get("strategy") or ""),
            str(meta.get("timeframe") or ""),
            str(meta.get("market") or ""),
            str(raw.get("metadata", {}).get("generated_at") or ""),
            str(path.stat().st_mtime_ns if path.exists() else ""),
        ]
    )
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _metric_pct(stats: dict[str, Any], *keys: str) -> float:
    for key in keys:
        if key in stats and stats[key] is not None:
            val = _to_float(stats[key])
            return round(val * 100 if abs(val) <= 3 else val, 4)
    return 0.0


def _metrics(raw: dict[str, Any]) -> dict[str, Any]:
    stats = raw.get("statistics") or raw.get("metrics") or {}
    if not isinstance(stats, dict):
        stats = {}
    return {
        "total_return_pct": _metric_pct(stats, "net_profit_pct", "total_return_pct"),
        "max_drawdown_pct": _metric_pct(stats, "max_drawdown_pct", "drawdown_pct"),
        "profit_factor": round(_to_float(stats.get("profit_factor")), 4),
        "sharpe": round(_to_float(stats.get("sharpe_ratio") or stats.get("sharpe")), 4),
        "sortino": round(_to_float(stats.get("sortino_ratio") or stats.get("sortino")), 4),
        "calmar": round(_to_float(stats.get("calmar_ratio") or stats.get("calmar")), 4),
        "win_rate_pct": _metric_pct(stats, "win_rate", "win_rate_pct"),
        "trades": int(_to_float(stats.get("total_trades") or stats.get("trades"))),
        "expectancy": round(_to_float(stats.get("expectancy") or stats.get("expectancy_pct")), 6),
        "recovery_factor": round(_to_float(stats.get("recovery_factor")), 4),
    }


def _equity_points(raw: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(raw.get("equity_curve") or []):
        if not isinstance(row, dict):
            continue
        ts = row.get("timestamp") or row.get("day") or row.get("date") or str(idx + 1)
        equity = _to_float(row.get("equity") or row.get("value"))
        out.append({"index": idx, "timestamp": str(ts), "equity": round(equity, 6)})
    return out


def _drawdown_points(equity: list[dict[str, Any]]) -> list[dict[str, Any]]:
    peak = 0.0
    out: list[dict[str, Any]] = []
    for row in equity:
        val = _to_float(row.get("equity"))
        peak = max(peak, val)
        dd = ((val - peak) / peak * 100) if peak > 0 else 0.0
        out.append({"timestamp": row.get("timestamp"), "drawdown_pct": round(dd, 4)})
    return out


def _asset_from_meta(meta: dict[str, Any]) -> str:
    if meta.get("base_asset"):
        return str(meta["base_asset"]).upper()
    market = str(meta.get("market") or "")
    return market.split("/")[0].upper() if "/" in market else "BTC"


def _params_from_meta(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "config_file": meta.get("config_file"),
        "risk_model": meta.get("risk_model"),
        "position_size": meta.get("position_size"),
        "risk_per_trade": meta.get("risk_per_trade"),
        "fee_rate": meta.get("fee_rate"),
        "slippage_rate": meta.get("slippage_rate"),
        "initial_capital": meta.get("initial_capital"),
        "data_years": meta.get("data_years"),
    }


def _experiment_from_report(path: Path, store: dict[str, Any], root: Path) -> dict[str, Any] | None:
    raw = _load_json(path)
    if not raw:
        return None
    meta = metadata_from_report_path(path, raw)
    period = period_from_report_raw(raw)
    exp_id = _experiment_id(path, raw, meta)
    ann = store.get("annotations", {}).get(exp_id, {})
    stat = _metrics(raw)
    return {
        "id": exp_id,
        "strategy": str(meta.get("strategy") or "unknown"),
        "strategy_label": str(meta.get("strategy_type") or meta.get("strategy") or "unknown"),
        "strategy_version": str(meta.get("strategy_version") or get_strategy_metadata(str(meta.get("strategy") or ""))["version"]),
        "parameters": _params_from_meta(meta),
        "timeframe": str(meta.get("timeframe") or "4h"),
        "asset": _asset_from_meta(meta),
        "quote": str(meta.get("quote") or "USDT").upper(),
        "market": str(meta.get("market") or ""),
        "period_start": period["period_start"],
        "period_end": period["period_end"],
        "period_days": period["period_days"],
        "code_version": str(meta.get("code_version") or _code_version(root)),
        "tested_at": str(meta.get("generated_at") or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()),
        "report_path": str(path.relative_to(root) if path.is_relative_to(root) else path),
        "metrics": stat,
        "tags": [t for t in ann.get("tags", []) if t in ALLOWED_TAGS],
        "note": str(ann.get("note") or ""),
        "updated_at": ann.get("updated_at"),
    }


def list_experiments(
    *,
    root: Path | None = None,
    reports_dir: Path | None = None,
    store_path: Path | None = None,
) -> dict[str, Any]:
    paths = _paths(root, reports_dir, store_path)
    store = _load_store(paths)
    items: list[dict[str, Any]] = []
    for path in sorted(paths.reports_dir.glob("*_report.json")):
        item = _experiment_from_report(path, store, paths.root)
        if item:
            items.append(item)
    items.sort(key=lambda i: str(i.get("tested_at") or ""), reverse=True)
    return {"items": items, "total": len(items), "allowed_tags": list(ALLOWED_TAGS)}


def update_experiment_annotation(
    experiment_id: str,
    *,
    tags: list[str] | None = None,
    note: str | None = None,
    root: Path | None = None,
    reports_dir: Path | None = None,
    store_path: Path | None = None,
) -> dict[str, Any]:
    paths = _paths(root, reports_dir, store_path)
    known = {item["id"] for item in list_experiments(root=paths.root, reports_dir=paths.reports_dir, store_path=paths.store_path)["items"]}
    if experiment_id not in known:
        raise KeyError(experiment_id)
    store = _load_store(paths)
    current = store["annotations"].setdefault(experiment_id, {})
    if tags is not None:
        current["tags"] = [tag for tag in tags if tag in ALLOWED_TAGS]
    if note is not None:
        current["note"] = note.strip()[:1000]
    current["updated_at"] = _now()
    _save_store(paths, store)
    return {"ok": True, "annotation": current}


def _reports_by_id(paths: LabPaths) -> dict[str, tuple[Path, dict[str, Any], dict[str, Any]]]:
    store = _load_store(paths)
    mapping: dict[str, tuple[Path, dict[str, Any], dict[str, Any]]] = {}
    for path in sorted(paths.reports_dir.glob("*_report.json")):
        raw = _load_json(path)
        if not raw:
            continue
        meta = metadata_from_report_path(path, raw)
        exp = _experiment_from_report(path, store, paths.root)
        if exp:
            mapping[exp["id"]] = (path, raw, exp)
    return mapping


def compare_experiments(
    experiment_ids: list[str],
    *,
    root: Path | None = None,
    reports_dir: Path | None = None,
    store_path: Path | None = None,
) -> dict[str, Any]:
    ids = [x for x in dict.fromkeys(experiment_ids) if x]
    if len(ids) < 2:
        raise ValueError("Selecione ao menos 2 experimentos.")
    paths = _paths(root, reports_dir, store_path)
    reports = _reports_by_id(paths)
    missing = [x for x in ids if x not in reports]
    if missing:
        raise KeyError(", ".join(missing))

    experiments: list[dict[str, Any]] = []
    curves: list[dict[str, Any]] = []
    drawdowns: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    for exp_id in ids:
        _, raw, exp = reports[exp_id]
        equity = _equity_points(raw)
        dd = _drawdown_points(equity)
        experiments.append(exp)
        curves.append({"id": exp_id, "label": f"{exp['strategy']} · {exp['asset']} · {exp['timeframe']}", "points": equity})
        drawdowns.append({"id": exp_id, "points": dd})
        metrics.append({"id": exp_id, **exp["metrics"]})
    ranked = sorted(metrics, key=lambda row: (_to_float(row.get("sharpe")), _to_float(row.get("total_return_pct"))), reverse=True)
    return {
        "experiments": experiments,
        "equity_curves": curves,
        "drawdown_curves": drawdowns,
        "metrics": metrics,
        "ranking": ranked,
        "best_id": ranked[0]["id"] if ranked else None,
    }


def strategy_replay(
    experiment_id: str,
    *,
    root: Path | None = None,
    reports_dir: Path | None = None,
    store_path: Path | None = None,
) -> dict[str, Any]:
    paths = _paths(root, reports_dir, store_path)
    reports = _reports_by_id(paths)
    if experiment_id not in reports:
        raise KeyError(experiment_id)
    _, raw, exp = reports[experiment_id]
    equity = _equity_points(raw)
    trades = [t for t in raw.get("trades") or [] if isinstance(t, dict)]
    entries: dict[str, list[dict[str, Any]]] = {}
    exits: dict[str, list[dict[str, Any]]] = {}
    for trade in trades:
        entries.setdefault(str(trade.get("entry_time") or "")[:10], []).append(trade)
        exits.setdefault(str(trade.get("exit_time") or "")[:10], []).append(trade)

    events: list[dict[str, Any]] = []
    for idx, point in enumerate(equity):
        day = str(point.get("timestamp") or "")[:10]
        day_entries = entries.get(day, [])
        day_exits = exits.get(day, [])
        signal = "hold"
        reason = "Sem novo sinal registrado"
        indicators: dict[str, Any] = {}
        if day_entries:
            trade = day_entries[0]
            signal = "entry"
            meta = trade.get("metadata") if isinstance(trade.get("metadata"), dict) else {}
            reason = str(meta.get("entry_reason") or trade.get("reason") or "Entrada registrada pelo backtest")
            indicators = dict(meta)
        elif day_exits:
            trade = day_exits[0]
            signal = "exit"
            meta = trade.get("metadata") if isinstance(trade.get("metadata"), dict) else {}
            reason = str(meta.get("exit_reason") or trade.get("reason") or "Saída registrada pelo backtest")
            indicators = dict(meta)
        events.append(
            {
                "index": idx,
                "timestamp": point.get("timestamp"),
                "equity": point.get("equity"),
                "signal": signal,
                "reason": reason,
                "entry_count": len(day_entries),
                "exit_count": len(day_exits),
                "indicators": indicators,
            }
        )
    return {"experiment": exp, "events": events, "total_events": len(events), "total_trades": len(trades)}


def strategy_library(
    *,
    root: Path | None = None,
    reports_dir: Path | None = None,
    store_path: Path | None = None,
) -> dict[str, Any]:
    paths = _paths(root, reports_dir, store_path)
    store = _load_store(paths)
    experiments = list_experiments(root=paths.root, reports_dir=paths.reports_dir, store_path=paths.store_path)["items"]
    by_strategy: dict[str, list[dict[str, Any]]] = {}
    for exp in experiments:
        by_strategy.setdefault(str(exp["strategy"]), []).append(exp)
    names = list(dict.fromkeys([*list_backtest_matrix_strategies(), *by_strategy.keys()]))
    items: list[dict[str, Any]] = []
    for name in names:
        meta = get_strategy_metadata(name)
        saved = store["strategies"].get(name, {})
        versions = sorted(
            {
                str(exp.get("strategy_version") or meta.get("version") or "1.0.0")
                for exp in by_strategy.get(name, [])
            }
            or {str(meta.get("version") or "1.0.0")}
        )
        items.append(
            {
                "id": name,
                "label": meta.get("type") or name,
                "status": saved.get("status") or ("active" if name == "quantum_trend_pro" else "experimental"),
                "market_type": get_market_type(name),
                "versions": versions,
                "experiment_count": len(by_strategy.get(name, [])),
                "last_tested_at": max((str(exp.get("tested_at") or "") for exp in by_strategy.get(name, [])), default=None),
                "note": saved.get("note") or meta.get("note") or "",
            }
        )
    return {"items": items, "statuses": list(ALLOWED_STATUSES)}


def update_strategy_status(
    strategy_id: str,
    *,
    status: str,
    note: str | None = None,
    root: Path | None = None,
    reports_dir: Path | None = None,
    store_path: Path | None = None,
) -> dict[str, Any]:
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Status inválido: {status}")
    paths = _paths(root, reports_dir, store_path)
    known = {item["id"] for item in strategy_library(root=paths.root, reports_dir=paths.reports_dir, store_path=paths.store_path)["items"]}
    if strategy_id not in known:
        raise KeyError(strategy_id)
    store = _load_store(paths)
    current = store["strategies"].setdefault(strategy_id, {})
    current["status"] = status
    if note is not None:
        current["note"] = note.strip()[:1000]
    current["updated_at"] = _now()
    _save_store(paths, store)
    return {"ok": True, "strategy": {"id": strategy_id, **current}}
