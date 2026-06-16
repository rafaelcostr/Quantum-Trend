from __future__ import annotations

from unittest.mock import MagicMock

from atlas.monitoring.alerts import TelegramAlerts
from atlas.monitoring.watchdog import AlertWatchdog


class FakeAlerts(TelegramAlerts):
    def __init__(self) -> None:
        self.enabled = True
        self.messages: list[str] = []

    def send(self, message: str, parse_mode: str | None = None) -> bool:
        self.messages.append(message)
        return True


def test_signal_alert_on_change_only():
    alerts = FakeAlerts()
    wd = AlertWatchdog(alerts, alert_on_signal=True, drawdown_alert_pct=0.10)

    wd.process(symbol="BTC/USDT", mode="paper", signal="hold", reason="wait", equity=5000)
    assert len(alerts.messages) == 0

    wd.process(symbol="BTC/USDT", mode="paper", signal="enter_long", reason="cross", equity=5000)
    assert len(alerts.messages) == 1
    assert "SINAL" in alerts.messages[0]

    # same signal again — no spam
    wd.process(symbol="BTC/USDT", mode="paper", signal="enter_long", reason="cross", equity=5000)
    assert len(alerts.messages) == 1


def test_signal_skipped_when_trade_executed():
    alerts = FakeAlerts()
    wd = AlertWatchdog(alerts, alert_on_signal=True, drawdown_alert_pct=0.10)

    wd.process(
        symbol="BTC/USDT",
        mode="paper",
        signal="enter_long",
        reason="cross",
        equity=5000,
        trade_executed=True,
    )
    assert len(alerts.messages) == 0


def test_drawdown_alert_once_with_recovery():
    alerts = FakeAlerts()
    wd = AlertWatchdog(alerts, alert_on_signal=False, drawdown_alert_pct=0.10)
    wd.reset_peak(5000)

    wd.process(symbol="BTC/USDT", mode="paper", signal="hold", reason="", equity=5000)
    assert len(alerts.messages) == 0

    wd.process(symbol="BTC/USDT", mode="paper", signal="hold", reason="", equity=4400)
    assert len(alerts.messages) == 1
    assert "DRAWDOWN" in alerts.messages[0]

    # still in drawdown — no repeat
    wd.process(symbol="BTC/USDT", mode="paper", signal="hold", reason="", equity=4300)
    assert len(alerts.messages) == 1

    # recover above 7.5% dd (75% of 10% threshold)
    wd.process(symbol="BTC/USDT", mode="paper", signal="hold", reason="", equity=4900)
    wd.process(symbol="BTC/USDT", mode="paper", signal="hold", reason="", equity=4400)
    assert len(alerts.messages) == 2
