from unittest.mock import MagicMock, patch

from atlas.monitoring.alerts import TelegramAlerts


def test_telegram_not_configured():
    alerts = TelegramAlerts()
    alerts.token = ""
    alerts.chat_id = ""
    assert alerts.configured is False
    assert alerts.send("test") is False


def test_notify_entry_format():
    alerts = TelegramAlerts()
    alerts.send_async = MagicMock()  # type: ignore[method-assign]
    alerts.notify_entry(
        symbol="BTC/USDT",
        entry_price=65000.0,
        strategy="MM200 Trend v2",
        reason="bullish cross",
        quote_spent=500.0,
    )
    alerts.send_async.assert_called_once()
    text = alerts.send_async.call_args[0][0]
    assert "Entrada LONG" in text
    assert "BTC/USDT" in text


@patch("urllib.request.urlopen")
def test_send_success(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp

    alerts = TelegramAlerts()
    alerts.token = "fake-token"
    alerts.chat_id = "12345"
    assert alerts.send("hello") is True
