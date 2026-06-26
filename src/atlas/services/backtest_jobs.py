from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from atlas.core.env import project_root
from atlas.core.log import logger
from atlas.services.backtest_batch import run_all_strategies_backtest
from atlas.strategies.metadata import list_backtest_matrix_strategies

ProgressCallback = Callable[[int, int, str], None]


@dataclass
class BacktestBatchJob:
    id: str
    status: str  # running | done | error
    total: int
    completed: int = 0
    current: str | None = None
    base_asset: str = "BTC"
    quote: str = "USDT"
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    updated_at: float = field(default_factory=time.time)


_jobs: dict[str, BacktestBatchJob] = {}
_lock = threading.Lock()
_active_job_id: str | None = None


def _infer_base_asset(raw: dict[str, Any]) -> str:
    explicit = raw.get("base_asset")
    if explicit:
        return str(explicit).upper()
    current = str(raw.get("current") or "")
    if current.startswith("ETH ·") or "ETH/" in current:
        return "ETH"
    if current.startswith("BTC ·") or "BTC/" in current:
        return "BTC"
    return "BTC"


def _is_job_live(job_id: str) -> bool:
    with _lock:
        return _active_job_id == job_id and job_id in _jobs and _jobs[job_id].status == "running"


def _recover_stale_persisted_job() -> None:
    path = _job_store_path()
    if not path.is_file():
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if raw.get("status") != "running":
        return
    job_id = str(raw.get("id") or "")
    if not job_id or _is_job_live(job_id):
        return
    job = _deserialize_job(raw)
    job.status = "error"
    job.error = "Job interrompido — a API foi reiniciada. Rode a matriz novamente."
    job.finished_at = time.time()
    _persist_job(job)
    logger.warning("Job órfão %s marcado como interrompido", job_id)


def _normalize_job_base(job: BacktestBatchJob) -> BacktestBatchJob:
    raw = {"base_asset": job.base_asset, "current": job.current}
    inferred = _infer_base_asset(raw)
    if job.base_asset.upper() != inferred:
        job.base_asset = inferred
    return job


def _job_store_path() -> Path:
    return project_root() / "data" / "runtime" / "backtest_job.json"


def _serialize_job(job: BacktestBatchJob) -> dict[str, Any]:
    return asdict(job)


def _deserialize_job(raw: dict[str, Any]) -> BacktestBatchJob:
    return BacktestBatchJob(
        id=str(raw["id"]),
        status=str(raw["status"]),
        total=int(raw.get("total") or 0),
        completed=int(raw.get("completed") or 0),
        current=raw.get("current"),
        base_asset=_infer_base_asset(raw),
        quote=str(raw.get("quote") or "USDT").upper(),
        result=raw.get("result"),
        error=raw.get("error"),
        started_at=float(raw.get("started_at") or time.time()),
        finished_at=float(raw["finished_at"]) if raw.get("finished_at") else None,
        updated_at=float(raw.get("updated_at") or time.time()),
    )


def _persist_job(job: BacktestBatchJob) -> None:
    job.updated_at = time.time()
    path = _job_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_serialize_job(job), ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _load_persisted_job(job_id: str) -> BacktestBatchJob | None:
    path = _job_store_path()
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if str(raw.get("id")) != job_id:
            return None
        return _deserialize_job(raw)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _set_job(job: BacktestBatchJob, *, persist: bool = True) -> None:
    with _lock:
        _jobs[job.id] = job
        if persist:
            _persist_job(job)


def get_backtest_batch_job(job_id: str) -> BacktestBatchJob | None:
    with _lock:
        job = _jobs.get(job_id)
    if job is not None:
        return job
    return _load_persisted_job(job_id)


def get_active_backtest_job() -> BacktestBatchJob | None:
    _recover_stale_persisted_job()
    with _lock:
        active_id = _active_job_id
    if not active_id:
        path = _job_store_path()
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if raw.get("status") == "running":
                    active_id = str(raw.get("id") or "")
            except (OSError, json.JSONDecodeError):
                active_id = None
    if not active_id:
        return None
    if not _is_job_live(active_id):
        return None
    job = get_backtest_batch_job(active_id)
    if job is None or job.status != "running":
        return None
    return _normalize_job_base(job)


def clear_backtest_job_cache() -> None:
    global _active_job_id
    with _lock:
        _jobs.clear()
        _active_job_id = None
    path = _job_store_path()
    if path.is_file():
        path.unlink(missing_ok=True)


def job_snapshot(job: BacktestBatchJob) -> dict[str, Any]:
    job = _normalize_job_base(job)
    base = job.base_asset.upper()
    quote = job.quote.upper()
    payload: dict[str, Any] = {
        "job_id": job.id,
        "status": job.status,
        "total": job.total,
        "completed": job.completed,
        "current": job.current,
        "base_asset": base,
        "quote": quote,
        "asset_label": f"{base}/{quote}",
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "updated_at": job.updated_at,
    }
    if job.status == "done" and job.result is not None:
        payload.update(job.result)
    if job.status == "error" and job.error:
        payload["error"] = job.error
    return payload


def start_backtest_batch_job(
    *,
    timeframes: tuple[str, ...],
    quote: str,
    base_asset: str = "BTC",
) -> str:
    global _active_job_id

    base_asset = base_asset.upper()
    quote = quote.upper()

    _recover_stale_persisted_job()

    existing = get_active_backtest_job()
    if existing is not None and existing.status == "running":
        if existing.base_asset.upper() != base_asset:
            raise RuntimeError(
                f"Matriz em execução para {existing.base_asset}/{existing.quote}. "
                f"Aguarde terminar antes de iniciar {base_asset}/{quote}."
            )
        logger.info("Reutilizando job de backtest em execução: %s (%s)", existing.id, existing.base_asset)
        return existing.id

    strategies = list_backtest_matrix_strategies()
    total = len(strategies) * len(timeframes)
    if total <= 0:
        raise RuntimeError("Nenhuma estratégia configurada para a matriz de backtests.")

    job_id = uuid.uuid4().hex[:12]
    job = BacktestBatchJob(
        id=job_id,
        status="running",
        total=total,
        current=f"Preparando matriz · {base_asset}/{quote}…",
        base_asset=base_asset,
        quote=quote,
    )
    with _lock:
        _active_job_id = job_id
    _set_job(job)

    def on_progress(completed: int, total_runs: int, current: str) -> None:
        with _lock:
            stored = _jobs.get(job_id)
            if stored is None:
                stored = _load_persisted_job(job_id)
            if stored is None:
                return
            stored.completed = completed
            stored.current = current
            stored.total = total_runs
            _jobs[job_id] = stored
        _persist_job(stored)

    def _run() -> None:
        global _active_job_id
        from atlas.services.terminal import clear_dashboard_cache, clear_intelligence_cache

        try:
            logger.info("Iniciando matriz de backtests (%s runs · %s/%s)", total, base_asset, quote)
            result = run_all_strategies_backtest(
                timeframes=timeframes,
                quote=quote,
                base_asset=base_asset,
                on_progress=on_progress,
            )
            clear_dashboard_cache()
            clear_intelligence_cache()
            with _lock:
                stored = _jobs.get(job_id) or _load_persisted_job(job_id)
                if stored is None:
                    return
                stored.status = "done"
                stored.completed = stored.total
                stored.current = None
                stored.result = result
                stored.finished_at = time.time()
                _jobs[job_id] = stored
            _persist_job(stored)
            logger.info(
                "Matriz concluída: %s/%s ok, %s falhas",
                result.get("completed"),
                result.get("total_runs"),
                result.get("failed"),
            )
        except Exception as exc:
            logger.exception("Matriz de backtests falhou")
            with _lock:
                stored = _jobs.get(job_id) or _load_persisted_job(job_id)
                if stored is None:
                    return
                stored.status = "error"
                stored.error = str(exc)
                stored.finished_at = time.time()
                _jobs[job_id] = stored
            _persist_job(stored)
        finally:
            with _lock:
                if _active_job_id == job_id:
                    _active_job_id = None

    threading.Thread(target=_run, daemon=True, name=f"backtest-batch-{job_id}").start()
    return job_id
