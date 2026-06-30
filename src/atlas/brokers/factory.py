"""Criação de brokers a partir da configuração operacional."""
from __future__ import annotations

from atlas.brokers.base import Broker, BrokerVenue, ExchangeId
from atlas.brokers.binance import BinanceDemoBroker, BinanceLiveBroker
from atlas.brokers.simulated import SimulatedBroker
from atlas.core.models import AtlasConfig, TradingMode


def broker_venue_for_config(config: AtlasConfig) -> BrokerVenue:
    explicit = (config.exchange.venue or "").strip().lower()
    if explicit:
        try:
            return BrokerVenue(explicit)
        except ValueError:
            pass
    if config.exchange.id.lower() == ExchangeId.SIMULATED.value:
        return BrokerVenue.PAPER_LOCAL
    if config.mode == TradingMode.LIVE:
        return BrokerVenue.LIVE_EXCHANGE
    return BrokerVenue.DEMO_EXCHANGE


def build_broker(config: AtlasConfig) -> Broker:
    exchange_id = (config.exchange.id or ExchangeId.BINANCE.value).strip().lower()
    venue = broker_venue_for_config(config)
    market_type = config.exchange.market_type or "spot"

    if exchange_id == ExchangeId.SIMULATED.value or venue == BrokerVenue.PAPER_LOCAL:
        return SimulatedBroker(
            symbol=config.exchange.symbol,
            execution=config.execution,
            market_type=market_type,
            venue=BrokerVenue.PAPER_LOCAL.value,
            cash=config.risk.initial_capital,
        )

    if exchange_id == ExchangeId.BINANCE.value:
        if config.mode == TradingMode.LIVE or venue == BrokerVenue.LIVE_EXCHANGE:
            return BinanceLiveBroker(config.exchange.symbol, market_type=market_type)
        return BinanceDemoBroker(config.exchange.symbol, market_type=market_type)

    supported = ", ".join([ExchangeId.BINANCE.value, ExchangeId.SIMULATED.value])
    future = ", ".join([ExchangeId.BYBIT.value, ExchangeId.OKX.value, ExchangeId.COINBASE.value])
    raise NotImplementedError(
        f"Exchange '{exchange_id}' ainda não implementada. Suportadas: {supported}. "
        f"Preparadas para extensão futura: {future}."
    )


def requires_exchange_credentials(config: AtlasConfig) -> bool:
    venue = broker_venue_for_config(config)
    exchange_id = (config.exchange.id or ExchangeId.BINANCE.value).strip().lower()
    return exchange_id == ExchangeId.BINANCE.value and venue in {
        BrokerVenue.DEMO_EXCHANGE,
        BrokerVenue.LIVE_EXCHANGE,
    }
