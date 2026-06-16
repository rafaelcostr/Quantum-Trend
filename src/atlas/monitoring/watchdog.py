from __future__ import annotations

from atlas.monitoring.alerts import TelegramAlerts


class AlertWatchdog:
    """Signal-change and drawdown threshold alerts (anti-spam)."""

    def __init__(
        self,
        alerts: TelegramAlerts,
        *,
        alert_on_signal: bool = True,
        drawdown_alert_pct: float = 0.10,
    ) -> None:
        self.alerts = alerts
        self.alert_on_signal = alert_on_signal
        self.drawdown_alert_pct = drawdown_alert_pct
        self._last_signal: str | None = None
        self._peak_equity: float = 0.0
        self._drawdown_alert_active = False

    def reset_peak(self, equity: float) -> None:
        self._peak_equity = max(self._peak_equity, equity)

    def process(
        self,
        *,
        symbol: str,
        mode: str,
        signal: str,
        reason: str,
        equity: float,
        trade_executed: bool = False,
    ) -> dict:
        """Evaluate alerts; returns metadata for journal/tick payload."""
        meta: dict = {"drawdown_pct": 0.0}

        self._peak_equity = max(self._peak_equity, equity)
        if self._peak_equity > 0:
            drawdown = (self._peak_equity - equity) / self._peak_equity
        else:
            drawdown = 0.0
        meta["drawdown_pct"] = drawdown
        meta["peak_equity"] = self._peak_equity

        if (
            self.alert_on_signal
            and signal in {"enter_long", "exit_long"}
            and signal != self._last_signal
            and not trade_executed
        ):
            self.alerts.signal_change(symbol, signal, reason, mode)
            meta["signal_alert"] = True

        self._last_signal = signal

        threshold = self.drawdown_alert_pct
        if threshold > 0 and drawdown >= threshold and not self._drawdown_alert_active:
            self.alerts.drawdown_alert(symbol, drawdown, equity, self._peak_equity, mode, threshold)
            self._drawdown_alert_active = True
            meta["drawdown_alert"] = True

        recover_level = threshold * 0.75
        if self._drawdown_alert_active and drawdown < recover_level:
            self._drawdown_alert_active = False
            meta["drawdown_recovered"] = True

        return meta
