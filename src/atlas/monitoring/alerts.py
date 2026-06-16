from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any


class TelegramAlerts:
    """Optional Telegram notifications for paper/live trading."""

    def __init__(self) -> None:
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.enabled = bool(self.token and self.chat_id)

    def send(self, message: str, parse_mode: str | None = None) -> bool:
        if not self.enabled:
            return False
        payload: dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": message,
            "disable_web_page_preview": True,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        data = urllib.parse.urlencode(payload).encode()
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode())
            return bool(body.get("ok"))
        except Exception:
            return False

    def trade_entry(
        self,
        symbol: str,
        price: float,
        quantity: float,
        reason: str,
        mode: str,
    ) -> bool:
        msg = (
            f"🟢 ATLAS {mode.upper()} — ENTRADA\n"
            f"{symbol}\n"
            f"Preço: ${price:,.2f}\n"
            f"Qtd: {quantity:.6f}\n"
            f"Motivo: {reason}"
        )
        return self.send(msg)

    def trade_exit(
        self,
        symbol: str,
        price: float,
        quantity: float,
        reason: str,
        mode: str,
    ) -> bool:
        msg = (
            f"🔴 ATLAS {mode.upper()} — SAÍDA\n"
            f"{symbol}\n"
            f"Preço: ${price:,.2f}\n"
            f"Qtd: {quantity:.6f}\n"
            f"Motivo: {reason}"
        )
        return self.send(msg)

    def error(self, symbol: str, error: str, mode: str) -> bool:
        msg = f"⚠️ ATLAS {mode.upper()} — ERRO\n{symbol}\n{error[:500]}"
        return self.send(msg)

    def drawdown_alert(
        self,
        symbol: str,
        drawdown_pct: float,
        equity: float,
        peak_equity: float,
        mode: str,
        threshold: float,
    ) -> bool:
        msg = (
            f"🚨 ATLAS {mode.upper()} — DRAWDOWN ALERTA\n"
            f"{symbol}\n"
            f"Drawdown: {drawdown_pct:.2%} (limite {threshold:.0%})\n"
            f"Equity: ${equity:,.2f}\n"
            f"Pico: ${peak_equity:,.2f}"
        )
        return self.send(msg)

    def signal_change(self, symbol: str, signal: str, reason: str, mode: str) -> bool:
        if signal not in {"enter_long", "exit_long"}:
            return False
        emoji = "🟢" if signal == "enter_long" else "🔴"
        label = "ENTRADA" if signal == "enter_long" else "SAÍDA"
        msg = (
            f"{emoji} ATLAS {mode.upper()} — SINAL {label} (sem ordem)\n"
            f"{symbol}\n"
            f"Preço avaliado no candle fechado\n"
            f"Motivo: {reason}"
        )
        return self.send(msg)
