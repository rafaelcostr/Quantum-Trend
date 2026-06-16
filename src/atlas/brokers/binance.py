from __future__ import annotations

import os
from datetime import datetime, timezone

import ccxt

from atlas.core.models import Candle, Order, OrderResult, Position, Side


class BinanceDemoBroker:
    """Binance demo trading via CCXT (enable_demo_trading)."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.exchange = ccxt.binance(
            {
                "apiKey": os.getenv("BINANCE_DEMO_API_KEY", ""),
                "secret": os.getenv("BINANCE_DEMO_API_SECRET", ""),
                "enableRateLimit": True,
            }
        )
        if hasattr(self.exchange, "enable_demo_trading"):
            self.exchange.enable_demo_trading(True)

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> list[Candle]:
        raw = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return [
            Candle(
                timestamp=datetime.fromtimestamp(r[0] / 1000, tz=timezone.utc),
                open=float(r[1]),
                high=float(r[2]),
                low=float(r[3]),
                close=float(r[4]),
                volume=float(r[5]),
            )
            for r in raw
        ]

    def get_balance(self) -> float:
        balance = self.exchange.fetch_balance()
        return float(balance.get("USDT", {}).get("free", 0))

    def get_account_balances(self) -> dict[str, float]:
        balance = self.exchange.fetch_balance()
        usdt = balance.get("USDT", {}) or {}
        btc = balance.get("BTC", {}) or {}
        return {
            "usdt_free": float(usdt.get("free", 0) or 0),
            "usdt_total": float(usdt.get("total", 0) or 0),
            "btc_free": float(btc.get("free", 0) or 0),
            "btc_total": float(btc.get("total", 0) or 0),
        }

    def check_connection(self) -> dict:
        """Test public + private API access (for diagnostics)."""
        result: dict = {"demo_url": self.exchange.urls.get("api")}
        try:
            rows = self.exchange.fetch_ohlcv(self.symbol, "4h", limit=1)
            result["ohlcv"] = "ok"
            result["last_close"] = float(rows[-1][4]) if rows else None
        except Exception as exc:
            result["ohlcv"] = f"fail: {exc}"

        try:
            balance = self.exchange.fetch_balance()
            result["balance"] = "ok"
            result["usdt_free"] = float(balance.get("USDT", {}).get("free", 0))
        except Exception as exc:
            result["balance"] = f"fail: {exc}"
        return result

    def get_position(self, symbol: str) -> Position | None:
        # Spot: position inferred from base asset balance (simplified)
        return None

    def place_order(self, order: Order) -> OrderResult:
        try:
            result = self.exchange.create_order(
                order.symbol,
                order.order_type,
                order.side.value,
                order.quantity,
                order.price,
            )
            return OrderResult(
                success=True,
                order_id=str(result.get("id")),
                filled_price=float(result.get("average") or result.get("price") or 0),
                filled_quantity=float(result.get("filled") or order.quantity),
            )
        except Exception as exc:
            return OrderResult(success=False, message=str(exc))

    def cancel_order(self, order_id: str) -> bool:
        try:
            self.exchange.cancel_order(order_id, self.symbol)
            return True
        except Exception:
            return False


class BinanceLiveBroker(BinanceDemoBroker):
    """Same interface as demo; uses live API keys — no demo flag."""

    def __init__(self, symbol: str) -> None:
        super().__init__(symbol)
        self.exchange = ccxt.binance(
            {
                "apiKey": os.getenv("BINANCE_LIVE_API_KEY", ""),
                "secret": os.getenv("BINANCE_LIVE_API_SECRET", ""),
                "enableRateLimit": True,
            }
        )
