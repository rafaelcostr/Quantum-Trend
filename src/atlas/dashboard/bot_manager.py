from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNTIME_DIR = Path("data/runtime")
PID_FILE = RUNTIME_DIR / "paper_bot.json"
LOG_FILE = RUNTIME_DIR / "paper_bot.log"


def _is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def bot_status() -> dict[str, Any]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if not PID_FILE.is_file():
        return {"running": False, "pid": None}
    try:
        data = json.loads(PID_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"running": False, "pid": None, "error": "pid file corrupt"}

    pid = int(data.get("pid", 0))
    alive = _is_alive(pid)
    if not alive:
        return {"running": False, "pid": pid, "stale": True, **data}
    return {"running": True, "pid": pid, **data}


def start_bot(project_root: Path, config_rel: str) -> dict[str, Any]:
    status = bot_status()
    if status.get("running"):
        return {"ok": False, "message": f"Bot ja rodando (PID {status['pid']})"}

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "atlas.runtime.paper_worker",
        "--config",
        config_rel,
    ]
    kwargs: dict[str, Any] = {"cwd": str(project_root)}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        kwargs["close_fds"] = False

    proc = subprocess.Popen(cmd, **kwargs)
    meta = {
        "pid": proc.pid,
        "config": config_rel,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    PID_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"ok": True, "message": f"Bot iniciado (PID {proc.pid})", **meta}


def stop_bot() -> dict[str, Any]:
    status = bot_status()
    pid = status.get("pid")
    if not pid or not status.get("running"):
        if PID_FILE.is_file():
            PID_FILE.unlink(missing_ok=True)
        return {"ok": True, "message": "Bot nao estava rodando"}

    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False, capture_output=True)
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

    PID_FILE.unlink(missing_ok=True)
    return {"ok": True, "message": f"Bot parado (PID {pid})"}


def tail_log(lines: int = 40) -> str:
    if not LOG_FILE.is_file():
        return "(sem log ainda)"
    text = LOG_FILE.read_text(encoding="utf-8", errors="replace")
    parts = text.strip().splitlines()
    return "\n".join(parts[-lines:]) if parts else "(vazio)"
