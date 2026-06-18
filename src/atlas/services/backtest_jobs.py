from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from atlas.services.backtest_batch import run_all_strategies_backtest
from atlas.strategies.registry import list_strategies


@dataclass
class BacktestBatchJob:
    id: str
    status: str  # running | done | error
    total: int
    completed: int = 0
    current: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None


_jobs: dict[str, BacktestBatchJob] = {}
_lock = threading.Lock()


def _set_job(job: BacktestBatchJob) -> None:
    with _lock:
        _jobs[job.id] = job


def get_backtest_batch_job(job_id: str) -> BacktestBatchJob | None:
    with _lock:
        return _jobs.get(job_id)


def clear_backtest_job_cache() -> None:
    with _lock:
        _jobs.clear()


def job_snapshot(job: BacktestBatchJob) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "job_id": job.id,
        "status": job.status,
        "total": job.total,
        "completed": job.completed,
        "current": job.current,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
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
) -> str:
    strategies = list_strategies()
    total = len(strategies) * len(timeframes)
    job_id = uuid.uuid4().hex[:12]
    job = BacktestBatchJob(id=job_id, status="running", total=total)
    _set_job(job)

    def on_progress(completed: int, current: str) -> None:
        with _lock:
            stored = _jobs.get(job_id)
            if stored is None:
                return
            stored.completed = completed
            stored.current = current

    def _run() -> None:
        from atlas.services.terminal import clear_dashboard_cache, clear_intelligence_cache

        try:
            result = run_all_strategies_backtest(
                timeframes=timeframes,
                quote=quote,
                on_progress=on_progress,
            )
            clear_dashboard_cache()
            clear_intelligence_cache()
            with _lock:
                stored = _jobs.get(job_id)
                if stored is None:
                    return
                stored.status = "done"
                stored.completed = stored.total
                stored.current = None
                stored.result = result
                stored.finished_at = time.time()
        except Exception as exc:
            with _lock:
                stored = _jobs.get(job_id)
                if stored is None:
                    return
                stored.status = "error"
                stored.error = str(exc)
                stored.finished_at = time.time()

    threading.Thread(target=_run, daemon=True).start()
    return job_id
