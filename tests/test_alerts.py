from __future__ import annotations

from atlas.monitoring.alerts import TelegramAlerts


def test_telegram_disabled_without_env(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    tg = TelegramAlerts()
    assert tg.enabled is False
    assert tg.send("test") is False


def test_telegram_enabled_with_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    tg = TelegramAlerts()
    assert tg.enabled is True
