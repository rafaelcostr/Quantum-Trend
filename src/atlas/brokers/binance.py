from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import ccxt
import pandas as pd

from atlas.core.env import get_settings
from atlas.core.external import ExternalErrorInfo, classify_external_error
from atlas.core.log import log_event, logger
from atlas.core.models import Candle, MarketTicker, Order, OrderResult, Position, Side
from atlas.core.symbols import operated_market_watchlist

ASSET_COLORS = {
    "BTC": "#F7931A",
    "ETH": "#627EEA",
    "SOL": "#14F195",
    "BNB": "#F0B90B",
    "XRP": "#23292F",
    "AVAX": "#E84142",
    "ADA": "#0033AD",
    "DOGE": "#C2A633",
    "LINK": "#2A5ADA",
    "DOT": "#E6007A",
    "ATOM": "#2E3148",
    "MATIC": "#8247E5",
}

WATCHLIST = operated_market_watchlist()


def _public_exchange() -> ccxt.binance:
    return ccxt.binance({"enableRateLimit": True, "timeout": 15000})


STABLECOINS = frozenset({"USDT", "USDC", "BUSD", "FDUSD", "USD", "TUSD"})


def _ensure_demo_trading(ex: ccxt.binance) -> ccxt.binance:
    if hasattr(ex, "enable_demo_trading"):
        ex.enable_demo_trading(True)
    return ex


def _live_exchange() -> ccxt.binance | None:
    settings = get_settings()
    if not settings.binance_live_api_key or not settings.binance_live_api_secret:
        return None
    return ccxt.binance(
        {
            "apiKey": settings.binance_live_api_key,
            "secret": settings.binance_live_api_secret,
            "enableRateLimit": True,
            "timeout": 15000,
            "options": {
                "defaultType": "spot",
                "adjustForTimeDifference": True,
                "recvWindow": 10000,
            },
        }
    )


def _demo_exchange() -> ccxt.binance | None:
    settings = get_settings()
    if not settings.binance_demo_api_key or not settings.binance_demo_api_secret:
        return None
    ex = ccxt.binance(
        {
            "apiKey": settings.binance_demo_api_key,
            "secret": settings.binance_demo_api_secret,
            "enableRateLimit": True,
            "timeout": 15000,
            "options": {
                "defaultType": "spot",
                "adjustForTimeDifference": True,
                "recvWindow": 10000,
            },
        }
    )
    return _ensure_demo_trading(ex)


def _balance_amount(balance: dict, asset: str, *, field: str = "total") -> float:
    """Lê saldo ccxt (estrutura unified ou nested free/used/total)."""
    asset = asset.upper()
    row = balance.get(asset)
    if isinstance(row, dict):
        return float(row.get(field, 0) or 0)
    bucket = balance.get(field)
    if isinstance(bucket, dict):
        return float(bucket.get(asset, 0) or 0)
    return 0.0


def _wallet_equity_usdt(ex: ccxt.binance, balance: dict | None = None) -> float:
    """Patrimônio spot estimado em USDT — alinhado ao 'Saldo estimado' da Binance."""
    balance = balance or ex.fetch_balance()
    totals = balance.get("total") or {}
    equity = 0.0
    to_price: list[tuple[str, float]] = []

    for asset, amount in totals.items():
        if asset in ("info", "timestamp", "datetime", "free", "used", "total"):
            continue
        if isinstance(amount, dict):
            amt = float(amount.get("total", 0) or 0)
        else:
            amt = float(amount or 0)
        if amt <= 1e-10:
            continue
        asset_u = str(asset).upper()
        if asset_u in STABLECOINS:
            equity += amt
        else:
            to_price.append((asset_u, amt))

    if not to_price:
        return equity

    symbols = [f"{asset}/USDT" for asset, _ in to_price]
    tickers: dict = {}
    try:
        tickers = ex.fetch_tickers(symbols)
    except Exception as exc:
        logger.debug("fetch_tickers wallet equity falhou: %s", exc)

    for asset, amt in to_price:
        sym = f"{asset}/USDT"
        ticker = tickers.get(sym) or {}
        price = float(ticker.get("last") or ticker.get("close") or 0)
        if price <= 0:
            try:
                ticker = ex.fetch_ticker(sym)
                price = float(ticker.get("last") or ticker.get("close") or 0)
            except Exception:
                price = 0.0
        equity += amt * price

    return equity


def _fetch_ohlcv_exchange(ex: ccxt.Exchange, symbol: str, timeframe: str, **kwargs) -> list[list]:
    try:
        return ex.fetch_ohlcv(symbol, timeframe=timeframe, **kwargs)
    except Exception as exc:
        logger.warning("fetch_ohlcv public falhou para %s: %s", symbol, exc)
        demo = _demo_exchange()
        if demo is None:
            raise
        return demo.fetch_ohlcv(symbol, timeframe=timeframe, **kwargs)


def fetch_ohlcv(symbol: str, timeframe: str = "4h", limit: int = 120) -> pd.DataFrame:
    ex = _public_exchange()
    rows = _fetch_ohlcv_exchange(ex, symbol, timeframe, limit=limit)
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def history_start_ms(ex: ccxt.Exchange, symbol: str, *, years: int = 0) -> int:
    """Epoch ms para início do download. years<=0 = todo histórico disponível na exchange."""
    if years > 0:
        start = datetime.now(timezone.utc).replace(microsecond=0) - pd.Timedelta(days=365 * years)
        return int(start.timestamp() * 1000)
    try:
        ex.load_markets()
        market = ex.market(symbol)
        created = market.get("created")
        if created:
            return int(created)
    except Exception as exc:
        logger.debug("history_start_ms fallback para %s: %s", symbol, exc)
    return ex.parse8601("2017-08-17T00:00:00Z")


def fetch_ohlcv_history(
    symbol: str,
    timeframe: str = "4h",
    *,
    years: int = 0,
    since_ms: int | None = None,
    until_ms: int | None = None,
    max_batches: int = 500,
) -> pd.DataFrame:
    """Baixa OHLCV paginado (Binance limita ~1000 candles por request)."""
    ex = _public_exchange()
    start = since_ms if since_ms is not None else history_start_ms(ex, symbol, years=years)
    end = until_ms or int(datetime.now(timezone.utc).timestamp() * 1000)
    batch_limit = 1000
    all_rows: list[list] = []
    cursor = start

    for batch_idx in range(max_batches):
        if cursor >= end:
            break
        batch = _fetch_ohlcv_exchange(ex, symbol, timeframe, since=cursor, limit=batch_limit)
        if not batch:
            break
        batch = [row for row in batch if row[0] < end]
        if not batch:
            break
        all_rows.extend(batch)
        last_ts = batch[-1][0]
        if len(batch) < batch_limit or last_ts >= end - 1:
            break
        cursor = last_ts + 1
        if batch_idx and batch_idx % 20 == 0:
            logger.info(
                "OHLCV %s %s: %s candles baixados ate %s",
                symbol,
                timeframe,
                len(all_rows),
                pd.to_datetime(last_ts, unit="ms", utc=True).date(),
            )

    if not all_rows:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df


def fetch_candles(symbol: str, timeframe: str = "4h", limit: int = 120) -> list[Candle]:
    df = fetch_ohlcv(symbol, timeframe, limit)
    return [
        Candle(
            timestamp=row.timestamp.to_pydatetime(),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
        )
        for row in df.itertuples()
    ]


def _sparkline_from_ticker(t: dict) -> list[float]:
    """Mini-gráfico a partir do ticker 24h — evita N chamadas OHLCV."""
    last = float(t.get("last") or t.get("close") or 0)
    if last <= 0:
        return []
    open_ = float(t.get("open") or last)
    high = float(t.get("high") or max(open_, last))
    low = float(t.get("low") or min(open_, last))
    mid = (open_ + last) / 2
    points = [open_, low, mid, high, last]
    lo, hi = min(points), max(points)
    if hi == lo:
        return [50.0] * len(points)
    return [40 + (c - lo) / (hi - lo) * 20 for c in points]


def _log_external_failure(event: str, exc: Exception, **fields: Any) -> ExternalErrorInfo:
    info = classify_external_error(exc)
    log_event(
        30,
        event,
        error_kind=info.kind,
        retryable=info.retryable,
        message=info.message,
        **fields,
    )
    return info


def fetch_tickers(symbols: list[str] | None = None, *, include_sparkline: bool = True) -> list[MarketTicker]:
    symbols = symbols or WATCHLIST
    ex = _public_exchange()
    try:
        tickers = ex.fetch_tickers(symbols)
    except Exception as exc:
        _LAST_TICKERS_ERROR[(tuple(symbols), include_sparkline)] = _log_external_failure(
            "external.binance.fetch_tickers.failed",
            exc,
            symbols=",".join(symbols),
        )
        return []

    out: list[MarketTicker] = []
    for sym in symbols:
        t = tickers.get(sym)
        if not t:
            continue
        spark = _sparkline_from_ticker(t) if include_sparkline else []
        out.append(
            MarketTicker(
                symbol=sym.split("/")[0],
                price=float(t.get("last") or t.get("close") or 0),
                change_pct=float(t.get("percentage") or 0),
                volume_24h=float(t.get("quoteVolume") or 0),
                sparkline=spark,
            )
        )
    return out


_TICKERS_CACHE: dict[tuple[tuple[str, ...], bool], tuple[float, list[MarketTicker], str]] = {}
_LAST_TICKERS_ERROR: dict[tuple[tuple[str, ...], bool], ExternalErrorInfo] = {}
_TICKERS_TTL = 30.0


def fetch_tickers_cached(
    symbols: list[str] | None = None,
    *,
    include_sparkline: bool = True,
    ttl: float = _TICKERS_TTL,
) -> list[MarketTicker]:
    symbols = symbols or WATCHLIST
    key = (tuple(symbols), include_sparkline)
    now = time.time()
    cached = _TICKERS_CACHE.get(key)
    if cached and (now - cached[0]) < ttl:
        _LAST_TICKERS_ERROR.pop(key, None)
        return cached[1]
    result = fetch_tickers(symbols, include_sparkline=include_sparkline)
    if result:
        _TICKERS_CACHE[key] = (now, result, datetime.now(timezone.utc).isoformat())
        _LAST_TICKERS_ERROR.pop(key, None)
        return result
    if cached:
        return cached[1]
    return result


def tickers_cache_status(
    symbols: list[str] | None = None,
    *,
    include_sparkline: bool = True,
    ttl: float = _TICKERS_TTL,
) -> dict[str, Any]:
    symbols = symbols or WATCHLIST
    key = (tuple(symbols), include_sparkline)
    cached = _TICKERS_CACHE.get(key)
    error = _LAST_TICKERS_ERROR.get(key)
    age = (time.time() - cached[0]) if cached else None
    return {
        "ttl_seconds": ttl,
        "stale": bool(error and cached),
        "age_seconds": round(age, 2) if age is not None else None,
        "last_success_at": cached[2] if cached else None,
        "error": error.model_dump() if error else None,
    }


def _sparkline(symbol: str, points: int = 20) -> list[float]:
    try:
        df = fetch_ohlcv(symbol, "1h", limit=points)
        closes = df["close"].tolist()
        if not closes:
            return []
        lo, hi = min(closes), max(closes)
        if hi == lo:
            return [50.0] * len(closes)
        return [40 + (c - lo) / (hi - lo) * 20 for c in closes]
    except Exception:
        return []


@dataclass
class AccountSnapshot:
    equity_usdt: float
    quote_total: float
    base_total: float
    quote_free: float
    base_free: float
    quote_asset: str
    base_asset: str


_SNAPSHOT_CACHE: dict[bool, AccountSnapshot | None] = {}
_SNAPSHOT_CACHE_AT: dict[bool, float] = {}
_SNAPSHOT_TTL = 35.0

_LAST_PRICE_CACHE: dict[str, tuple[float, float]] = {}
_LAST_PRICE_TTL = 8.0


def fetch_last_price(symbol: str = "BTC/USDT") -> float:
    now = time.time()
    cached = _LAST_PRICE_CACHE.get(symbol)
    if cached and (now - cached[1]) < _LAST_PRICE_TTL:
        return cached[0]
    try:
        ticker = _public_exchange().fetch_ticker(symbol)
        price = float(ticker.get("last") or ticker.get("close") or 0)
        if price > 0:
            _LAST_PRICE_CACHE[symbol] = (price, now)
        return price
    except Exception as exc:
        info = classify_external_error(exc)
        log_event(
            10,
            "external.binance.fetch_last_price.failed",
            symbol=symbol,
            error_kind=info.kind,
            message=info.message,
        )
        return cached[0] if cached else 0.0


def fetch_account_snapshot(symbol: str = "BTC/USDT", *, live: bool = False, force: bool = False) -> AccountSnapshot | None:
    global _SNAPSHOT_CACHE, _SNAPSHOT_CACHE_AT
    now = time.time()
    cached = _SNAPSHOT_CACHE.get(live)
    cached_at = _SNAPSHOT_CACHE_AT.get(live, 0.0)
    if not force and cached is not None and (now - cached_at) < _SNAPSHOT_TTL:
        return cached

    ex = _live_exchange() if live else _demo_exchange()
    if ex is None:
        log_event(
            30,
            "external.binance.credentials.missing",
            mode="live" if live else "paper",
            symbol=symbol,
        )
        return None
    try:
        balance = ex.fetch_balance()
        base, quote = symbol.split("/")
        quote_total = _balance_amount(balance, quote, field="total")
        base_total = _balance_amount(balance, base, field="total")
        quote_free = _balance_amount(balance, quote, field="free")
        base_free = _balance_amount(balance, base, field="free")
        equity = _wallet_equity_usdt(ex, balance)
        snap = AccountSnapshot(
            equity_usdt=equity,
            quote_total=quote_total,
            base_total=base_total,
            quote_free=quote_free,
            base_free=base_free,
            quote_asset=quote,
            base_asset=base,
        )
        _SNAPSHOT_CACHE[live] = snap
        _SNAPSHOT_CACHE_AT[live] = now
        return snap
    except Exception as exc:
        label = "live" if live else "demo"
        _log_external_failure(
            "external.binance.fetch_account_snapshot.failed",
            exc,
            mode=label,
            symbol=symbol,
        )
        return None


def asset_color(symbol: str) -> str:
    base = symbol.split("/")[0] if "/" in symbol else symbol
    return ASSET_COLORS.get(base.upper(), "#7C3AED")


def market_buy_quote(symbol: str, quote_amount: float) -> dict | None:
    ex = _demo_exchange()
    if ex is None or quote_amount <= 0:
        return None
    try:
        return ex.create_order(
            symbol, "market", "buy", None, None, {"quoteOrderQty": round(quote_amount, 2)}
        )
    except Exception as exc:
        _log_external_failure("external.binance.market_buy.failed", exc, symbol=symbol)
        return None


def market_sell_base(symbol: str, base_amount: float) -> dict | None:
    ex = _demo_exchange()
    if ex is None or base_amount <= 0:
        return None
    try:
        return ex.create_market_sell_order(symbol, base_amount)
    except Exception as exc:
        _log_external_failure("external.binance.market_sell.failed", exc, symbol=symbol)
        return None


def live_api_connected(symbol: str = "BTC/USDT") -> bool:
    return credentials_configured(live=True) and fetch_account_snapshot(symbol, live=True) is not None


def demo_api_connected() -> bool:
    return _demo_exchange() is not None


def credentials_configured(*, live: bool = False) -> bool:
    settings = get_settings()
    if live:
        return bool(settings.binance_live_api_key and settings.binance_live_api_secret)
    return bool(settings.binance_demo_api_key and settings.binance_demo_api_secret)


def fetch_public_candles(symbol: str, timeframe: str, limit: int = 500) -> list[Candle]:
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


class BinanceDemoBroker:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def _exchange(self) -> ccxt.binance:
        ex = _demo_exchange()
        if ex is None:
            raise RuntimeError("Chaves Binance Demo ausentes no .env")
        return ex

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
            except Exception as exc:
                logger.debug("fetch_candles demo falhou, usando API publica: %s", exc)
        return fetch_public_candles(symbol, timeframe, limit)

    def get_balance(self) -> float:
        balance = self._exchange().fetch_balance()
        quote = self.symbol.split("/")[-1].upper()
        return _balance_amount(balance, quote, field="free")

    def get_position(self, symbol: str) -> Position | None:
        base = symbol.split("/")[0].upper()
        balance = self._exchange().fetch_balance()
        qty = _balance_amount(balance, base, field="total")
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
        except Exception as exc:
            _log_external_failure("external.binance.cancel_order.failed", exc, order_id=order_id)
            return False

    def fetch_open_orders(self, symbol: str) -> list[dict]:
        try:
            raw = self._exchange().fetch_open_orders(symbol)
            out: list[dict] = []
            for order in raw or []:
                out.append(
                    {
                        "id": str(order.get("id", "")),
                        "type": str(order.get("type", "")),
                        "side": str(order.get("side", "")),
                        "price": float(order.get("price") or 0),
                        "amount": float(order.get("amount") or 0),
                        "status": str(order.get("status", "")),
                    }
                )
            return out
        except Exception as exc:
            _log_external_failure("external.binance.fetch_open_orders.failed", exc, symbol=symbol)
            return [{"error": str(exc)}]


class BinanceLiveBroker(BinanceDemoBroker):
    def _exchange(self) -> ccxt.binance:
        ex = _live_exchange()
        if ex is None:
            raise RuntimeError("Chaves Binance Live ausentes no .env")
        return ex
