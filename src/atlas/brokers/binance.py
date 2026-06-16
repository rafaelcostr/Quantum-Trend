from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache

import ccxt

from atlas.core.models import Candle, Order, OrderResult, Position, Side


def demo_credentials() -> tuple[str, str]:
    return (
        os.getenv("BINANCE_DEMO_API_KEY", "").strip(),
        os.getenv("BINANCE_DEMO_API_SECRET", "").strip(),
    )


def live_credentials() -> tuple[str, str]:
    return (
        os.getenv("BINANCE_LIVE_API_KEY", "").strip(),
        os.getenv("BINANCE_LIVE_API_SECRET", "").strip(),
    )


def credentials_configured(*, live: bool = False) -> bool:
    key, secret = live_credentials() if live else demo_credentials()
    return bool(key and secret)


@lru_cache(maxsize=1)
def _public_exchange() -> ccxt.binance:
    return ccxt.binance({"enableRateLimit": True})


def fetch_public_candles(symbol: str, timeframe: str, limit: int = 500) -> list[Candle]:
    """OHLCV via API publica Binance — nao exige API key (graficos do dashboard)."""
    raw = _public_exchange().fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
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


def _build_exchange(*, demo: bool) -> ccxt.binance:
    if demo:
        key, secret = demo_credentials()
    else:
        key, secret = live_credentials()
    exchange = ccxt.binance(
        {
            "apiKey": key,
            "secret": secret,
            "enableRateLimit": True,
        }
    )
    if demo and hasattr(exchange, "enable_demo_trading"):
        exchange.enable_demo_trading(True)
    return exchange


class BinanceDemoBroker:
    """Binance demo trading via CCXT (enable_demo_trading)."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def _exchange(self) -> ccxt.binance:
        key, secret = demo_credentials()
        if not key or not secret:
            raise RuntimeError(
                "Chaves Binance Demo ausentes. Preencha BINANCE_DEMO_API_KEY e "
                "BINANCE_DEMO_API_SECRET no arquivo .env na raiz do projeto."
            )
        return _build_exchange(demo=True)

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> list[Candle]:
        if credentials_configured(live=False):
            try:
                raw = self._exchange().fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
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
            except Exception:
                pass
        return fetch_public_candles(symbol, timeframe, limit)

    def get_balance(self) -> float:
        balance = self._exchange().fetch_balance()
        return float(balance.get("USDT", {}).get("free", 0))

    def get_account_balances(self) -> dict[str, float]:
        balance = self._exchange().fetch_balance()
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
        result: dict = {}
        try:
            rows = fetch_public_candles(self.symbol, "4h", limit=1)
            result["ohlcv"] = "ok"
            result["last_close"] = rows[-1].close if rows else None
        except Exception as exc:
            result["ohlcv"] = f"fail: {exc}"

        if not credentials_configured(live=False):
            result["balance"] = "fail: API keys missing in .env"
            return result

        try:
            ex = self._exchange()
            result["demo_url"] = ex.urls.get("api")
            balance = ex.fetch_balance()
            result["balance"] = "ok"
            result["usdt_free"] = float(balance.get("USDT", {}).get("free", 0))
        except Exception as exc:
            result["balance"] = f"fail: {exc}"
        return result

    def get_position(self, symbol: str) -> Position | None:
        base = symbol.split("/")[0].upper()
        balance = self._exchange().fetch_balance()
        asset = balance.get(base, {}) or {}
        qty = float(asset.get("total", 0) or 0)
        if qty <= 0.0001:
            return None
        return Position(
            symbol=symbol,
            side=Side.BUY,
            quantity=qty,
            entry_price=0.0,
            entry_time=datetime.now(timezone.utc),
            metadata={"source": "exchange_balance"},
        )

    def place_order(self, order: Order) -> OrderResult:
        try:
            result = self._exchange().create_order(
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
            self._exchange().cancel_order(order_id, self.symbol)
            return True
        except Exception:
            return False


class BinanceLiveBroker(BinanceDemoBroker):
    """Live API keys — sem flag demo."""

    def _exchange(self) -> ccxt.binance:
        key, secret = live_credentials()
        if not key or not secret:
            raise RuntimeError(
                "Chaves Binance Live ausentes. Preencha BINANCE_LIVE_API_KEY e "
                "BINANCE_LIVE_API_SECRET no .env."
            )
        return _build_exchange(demo=False)

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> list[Candle]:
        if credentials_configured(live=True):
            try:
                raw = self._exchange().fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
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
            except Exception:
                pass
        return fetch_public_candles(symbol, timeframe, limit)

    def check_connection(self) -> dict:
        result = super().check_connection()
        if credentials_configured(live=True):
            try:
                result["demo_url"] = self._exchange().urls.get("api")
            except Exception:
                pass
        return result
