from __future__ import annotations

from atlas.monitoring.watchdog import AlertWatchdog


class FakeAlerts:
    def __init__(self) -> None:
        self.messages: list[str] = []

    @property
    def configured(self) -> bool:
        return True

    def send_async(self, message: str) -> None:
        self.messages.append(message)

    def signal_change(self, symbol: str, signal: str, reason: str, mode: str) -> None:
        self.messages.append(f"SINAL {signal} {symbol} {reason}")

    def drawdown_alert(
        self,
        symbol: str,
        drawdown: float,
        equity: float,
        peak: float,
        mode: str,
        threshold: float,
    ) -> None:
        self.messages.append(f"DRAWDOWN {drawdown:.1%} {symbol}")


def test_signal_alert_on_change_only():
    alerts = FakeAlerts()
    wd = AlertWatchdog(alerts, alert_on_signal=True, drawdown_alert_pct=0.10)

    wd.process(symbol="BTC/USDT", mode="paper", signal="hold", reason="wait", equity=5000)
    assert len(alerts.messages) == 0

    wd.process(symbol="BTC/USDT", mode="paper", signal="enter_long", reason="cross", equity=5000)
    assert len(alerts.messages) == 1
    assert "SINAL" in alerts.messages[0]

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

    wd.process(symbol="BTC/USDT", mode="paper", signal="hold", reason="", equity=4300)
    assert len(alerts.messages) == 1

    wd.process(symbol="BTC/USDT", mode="paper", signal="hold", reason="", equity=4900)
    wd.process(symbol="BTC/USDT", mode="paper", signal="hold", reason="", equity=4400)
    assert len(alerts.messages) == 2
