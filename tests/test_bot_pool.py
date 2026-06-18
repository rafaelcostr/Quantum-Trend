from __future__ import annotations

from unittest.mock import MagicMock, patch

from atlas.core.models import TradingMode
from atlas.runtime.bot_runner import BotRunnerPool


def test_start_all_does_not_deadlock_on_stop():
    pool = BotRunnerPool()
    cfg = MagicMock()
    cfg.strategy.name = "mm200_trend_v2"
    cfg.exchange.timeframe = "4h"
    cfg.mode = TradingMode.PAPER
    cfg.runtime.poll_seconds = 1

    with patch.object(BotRunnerPool, "_stop_all_unlocked") as stop_mock:
        with patch("atlas.runtime.bot_runner.BotRunner") as runner_cls:
            runner = MagicMock()
            runner_cls.return_value = runner
            pool.start_all(mode=TradingMode.PAPER, configs=[("mm200_trend_v2_4h", cfg)])
            stop_mock.assert_called_once()
            runner.start.assert_called_once()


def test_stop_all_clears_runners():
    pool = BotRunnerPool()
    runner = MagicMock()
    runner.is_alive.return_value = False
    pool._runners["a"] = runner
    pool._mode = TradingMode.PAPER

    pool.stop_all()

    runner.stop.assert_called_once()
    assert pool._runners == {}
    assert pool._mode is None
