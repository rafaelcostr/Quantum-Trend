"""Config operacional — estrategia, par e timeframe."""
from __future__ import annotations

from pathlib import Path

import yaml

from atlas.core.config import AtlasConfig, load_config
from atlas.core.symbols import QUOTE_ASSETS, quote_from_symbol
from atlas.strategies.registry import STRATEGY_BUILDERS

ACTIVE_CONFIG_REL = "data/runtime/active_paper.yaml"
TIMEFRAMES = ("1h", "4h", "1d")


def _config_dir(project_root: Path) -> Path:
    return project_root / "config"


def discover_strategy_configs(project_root: Path) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for path in sorted(_config_dir(project_root).glob("backtest*.yaml")):
        try:
            cfg = load_config(path)
            mapping[cfg.strategy.name] = path
        except Exception:
            continue
    return mapping


def list_strategy_names(project_root: Path) -> list[str]:
    names = sorted(discover_strategy_configs(project_root).keys())
    if not names:
        return sorted(STRATEGY_BUILDERS.keys())
    return names


def build_operational_config(
    project_root: Path,
    *,
    strategy_name: str,
    quote_asset: str = "USDT",
    timeframe: str = "4h",
    base_config_rel: str = "config/paper.yaml",
) -> AtlasConfig:
    base = load_config(project_root / base_config_rel)
    strategy_map = discover_strategy_configs(project_root)

    if strategy_name in strategy_map:
        src = load_config(strategy_map[strategy_name])
        base.strategy = src.strategy
    elif strategy_name in STRATEGY_BUILDERS:
        base.strategy.name = strategy_name
    else:
        raise ValueError(f"Estrategia desconhecida: {strategy_name}")

    quote = quote_asset.upper()
    if quote not in QUOTE_ASSETS:
        raise ValueError(f"Quote invalido: {quote}. Use USDT ou USDC.")

    tf = timeframe.lower()
    if tf not in TIMEFRAMES:
        raise ValueError(f"Timeframe invalido: {tf}. Use 1h, 4h ou 1d.")

    base.exchange.symbol = f"BTC/{quote}"
    base.exchange.timeframe = tf
    base.exchange.demo = True
    return base


def save_config_yaml(path: Path, config: AtlasConfig) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(mode="json")
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return path
