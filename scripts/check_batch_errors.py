from __future__ import annotations

import json
from pathlib import Path

from atlas.core.env import project_root
from atlas.services.backtest_batch import run_all_strategies_backtest


def main() -> None:
    job_path = project_root() / "data" / "runtime" / "backtest_job.json"
    if job_path.is_file():
        raw = json.loads(job_path.read_text(encoding="utf-8"))
        result = raw.get("result") or {}
        print("=== LAST JOB ON DISK ===")
        print("status:", raw.get("status"))
        print("completed:", result.get("completed"), "/", result.get("total_runs"))
        print("failed:", result.get("failed"))
        for e in result.get("errors", []):
            print(" -", e.get("strategy"), e.get("timeframe"), "->", e.get("error"))
        print()

    print("=== RE-RUN CHECK (may take a while) ===")
    result = run_all_strategies_backtest(timeframes=("1h", "4h", "1d"), quote="USDT")
    print("total:", result["total_runs"], "ok:", result["completed"], "failed:", result["failed"])
    for e in result.get("errors", []):
        print("FAIL:", e.get("strategy"), e.get("timeframe"), "->", e.get("error"))


if __name__ == "__main__":
    main()
