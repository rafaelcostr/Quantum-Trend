from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("atlas")


def log_event(level: int, event: str, **fields: Any) -> None:
    """Log estruturado leve, mantendo compatibilidade com handlers texto."""
    clean = {k: v for k, v in fields.items() if v is not None}
    suffix = " ".join(f"{k}={v}" for k, v in clean.items())
    logger.log(level, "%s%s", event, f" {suffix}" if suffix else "")
