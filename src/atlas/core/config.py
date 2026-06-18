from __future__ import annotations

from pathlib import Path

import yaml

from atlas.core.env import project_root
from atlas.core.models import AtlasConfig, TradingMode


def load_config(path: Path | str) -> AtlasConfig:
    cfg_path = Path(path)
    if not cfg_path.is_absolute():
        cfg_path = project_root() / cfg_path
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    return AtlasConfig.model_validate(raw)


def default_paper_config() -> AtlasConfig:
    return load_config(project_root() / "config" / "paper.yaml")


def default_config_for_mode(mode: TradingMode, root: Path | None = None) -> AtlasConfig:
    base = root or project_root()
    filename = {
        TradingMode.BACKTEST: "backtest.yaml",
        TradingMode.PAPER: "paper.yaml",
        TradingMode.LIVE: "live.yaml",
    }[mode]
    return load_config(base / "config" / filename)
