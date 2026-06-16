from __future__ import annotations

from atlas.core.config import AtlasConfig
from atlas.runtime.engine import TradingEngine


class TradingRunner:
    """24/7 paper or live trading via TradingEngine."""

    def __init__(self, config: AtlasConfig) -> None:
        self.engine = TradingEngine(config)

    def run(self) -> None:
        self.engine.run_forever()

    def tick(self) -> dict:
        """Single evaluation cycle (useful for tests)."""
        return self.engine.process_once()
