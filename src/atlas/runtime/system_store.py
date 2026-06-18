from __future__ import annotations

import json
from dataclasses import dataclass, field

from atlas.core.env import project_root

_PATH = project_root() / "data" / "runtime" / "system.json"


@dataclass
class RuntimeSystemSettings:
    kill_switch: bool | None = None
    notifications: dict[str, bool] = field(default_factory=dict)


def _load_raw() -> dict:
    if not _PATH.is_file():
        return {}
    try:
        return json.loads(_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_runtime_system() -> RuntimeSystemSettings:
    raw = _load_raw()
    return RuntimeSystemSettings(
        kill_switch=raw.get("kill_switch"),
        notifications=dict(raw.get("notifications") or {}),
    )


def save_runtime_system(**kwargs) -> RuntimeSystemSettings:
    raw = _load_raw()
    if "kill_switch" in kwargs and kwargs["kill_switch"] is not None:
        raw["kill_switch"] = bool(kwargs["kill_switch"])
    if "notifications" in kwargs and kwargs["notifications"] is not None:
        raw["notifications"] = {**raw.get("notifications", {}), **kwargs["notifications"]}
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    return get_runtime_system()
