from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from atlas.research.walkforward import WalkForwardResult, walk_forward_to_dict


def walkforward_path(reports_dir: Path, strategy: str) -> Path:
    return reports_dir / f"{strategy}_walkforward.json"


def save_walkforward(wf: WalkForwardResult, reports_dir: str | Path) -> Path:
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = walkforward_path(reports_dir, wf.strategy)
    path.write_text(json.dumps(walk_forward_to_dict(wf), indent=2), encoding="utf-8")
    return path


def load_walkforward(reports_dir: str | Path, strategy: str) -> dict[str, Any] | None:
    path = walkforward_path(Path(reports_dir), strategy)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
