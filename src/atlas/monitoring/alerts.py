from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from typing import Any

from atlas.core.env import get_settings
from atlas.core.log import logger


class TelegramAlerts:
    """Envia alertas via Bot API do Telegram."""

    def __init__(self) -> None:
        settings = get_settings()
        self.token = (settings.telegram_bot_token or "").strip()
        self.chat_id = (settings.telegram_chat_id or "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, text: str, *, parse_mode: str = "HTML") -> bool:
        if not self.configured:
            logger.debug("Telegram não configurado — alerta ignorado")
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = json.dumps(
            {"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            logger.warning("Telegram HTTP %s: %s", exc.code, body)
            return False
        except Exception as exc:
            logger.warning("Telegram falhou: %s", exc)
            return False

    def send_async(self, text: str) -> None:
        threading.Thread(target=self.send, args=(text,), daemon=True).start()

    def notify_test(self) -> bool:
        return self.send("✅ <b>Quantum-Trend</b>\nAlertas Telegram configurados corretamente.")

    def notify_bot_started(self, *, strategy: str, symbol: str, mode: str = "Paper (Binance Demo)") -> None:
        self.send_async(
            f"🟢 <b>Bot iniciado</b>\n"
            f"Estratégia: {strategy}\n"
            f"Par: {symbol}\n"
            f"Modo: {mode}"
        )

    def notify_bot_stopped(self, *, strategy: str, mode: str = "paper") -> None:
        self.send_async(f"🛑 <b>Bot parado</b>\nEstratégia: {strategy}\nModo: {mode}")

    def notify_entry(
        self,
        *,
        symbol: str,
        entry_price: float,
        strategy: str,
        reason: str,
        quote_spent: float | None = None,
    ) -> None:
        spend = f"\nValor: ${quote_spent:,.2f}" if quote_spent else ""
        self.send_async(
            f"📈 <b>Entrada LONG</b>\n"
            f"Ativo: {symbol}\n"
            f"Preço: ${entry_price:,.4f}{spend}\n"
            f"Estratégia: {strategy}\n"
            f"Sinal: {reason}"
        )

    def notify_exit(
        self,
        *,
        symbol: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        strategy: str,
        reason: str,
    ) -> None:
        pnl_pct = ((exit_price / entry_price) - 1) * 100 if entry_price else 0
        emoji = "💰" if pnl >= 0 else "📉"
        sign = "+" if pnl >= 0 else ""
        self.send_async(
            f"{emoji} <b>Saída LONG</b>\n"
            f"Ativo: {symbol}\n"
            f"Entrada: ${entry_price:,.4f}\n"
            f"Saída: ${exit_price:,.4f}\n"
            f"P&L: {sign}${pnl:,.2f} ({sign}{pnl_pct:.2f}%)\n"
            f"Estratégia: {strategy}\n"
            f"Sinal: {reason}"
        )

    def notify_error(self, message: str) -> None:
        self.send_async(f"⚠️ <b>Erro do bot</b>\n{message}")

    @property
    def enabled(self) -> bool:
        return self.configured

    def trade_entry(
        self,
        symbol: str,
        price: float,
        quantity: float,
        reason: str,
        mode: str,
    ) -> None:
        self.notify_entry(
            symbol=symbol,
            entry_price=price,
            strategy=mode,
            reason=reason,
            quote_spent=price * quantity,
        )

    def trade_exit(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        reason: str,
        mode: str,
    ) -> None:
        pnl = (exit_price - entry_price) * quantity
        self.notify_exit(
            symbol=symbol,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            strategy=mode,
            reason=reason,
        )

    def signal_change(self, symbol: str, signal: str, reason: str, mode: str) -> None:
        self.send_async(f"📡 <b>Sinal</b> {signal}\n{symbol} · {mode}\n{reason}")

    def drawdown_alert(
        self,
        symbol: str,
        drawdown: float,
        equity: float,
        peak: float,
        mode: str,
        threshold: float,
    ) -> None:
        self.send_async(
            f"⚠️ <b>Drawdown</b> {drawdown:.1%}\n"
            f"{symbol} · {mode}\nEquity: ${equity:,.2f} (pico ${peak:,.2f})"
        )

    def error(self, symbol: str, message: str, mode: str) -> None:
        self.notify_error(f"{symbol} ({mode}): {message}")


_alerts: TelegramAlerts | None = None


def get_alerts() -> TelegramAlerts:
    global _alerts
    if _alerts is None:
        _alerts = TelegramAlerts()
    return _alerts
