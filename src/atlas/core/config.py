from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from atlas.core.models import TradingMode


class ExchangeConfig(BaseModel):
    id: str = "binance"
    symbol: str = "BTC/USDT"
    timeframe: str = "4h"
    demo: bool = False


class StrategyConfig(BaseModel):
    name: str = "range_hunter_v1"
    params: dict[str, Any] = Field(default_factory=dict)


class RiskConfig(BaseModel):
    initial_capital: float = 10_000.0
    risk_per_trade: float = 0.01
    max_open_positions: int = 1
    max_daily_drawdown: float = 0.03
    max_weekly_drawdown: float = 0.08
    sizing_mode: str = "risk_based"  # risk_based | full_equity


class ExecutionConfig(BaseModel):
    fee_rate: float = 0.001
    slippage_rate: float = 0.0005
    entry_on_next_open: bool = True
    use_exchange_stop: bool = False


class DataConfig(BaseModel):
    years: int = 3
    cache_dir: str = "data/cache"


class RuntimeConfig(BaseModel):
    poll_seconds: int = 60
    reconcile_minutes: int = 15
    alert_on_signal: bool = True
    drawdown_alert_pct: float = 0.10


class AtlasConfig(BaseModel):
    mode: TradingMode = TradingMode.BACKTEST
    exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    database_url: str = "postgresql://atlas:atlas@localhost:15432/atlas_quant"


def load_config(path: str | Path) -> AtlasConfig:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return AtlasConfig.model_validate(raw)


def default_config_for_mode(mode: TradingMode, project_root: Path | None = None) -> AtlasConfig:
    root = project_root or Path.cwd()
    filename = {
        TradingMode.BACKTEST: "backtest.yaml",
        TradingMode.PAPER: "paper.yaml",
        TradingMode.LIVE: "live.yaml",
    }[mode]
    return load_config(root / "config" / filename)
