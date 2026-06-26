from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def cache_meta(*, generated_at: float, ttl: float, last_success_at: str | None, stale: bool = False) -> dict[str, Any]:
    return {
        "stale": stale,
        "ttl_seconds": ttl,
        "generated_at": generated_at,
        "last_success_at": last_success_at,
    }
