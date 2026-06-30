from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from atlas.core.models import Position, RiskConfig, Side


@dataclass
class ExposureSnapshot:
    total_usdt: float = 0.0
    by_asset: dict[str, float] = field(default_factory=dict)
    by_direction: dict[str, float] = field(default_factory=dict)
    by_timeframe: dict[str, float] = field(default_factory=dict)
    by_strategy: dict[str, float] = field(default_factory=dict)
    correlated_usdt: float = 0.0
    positions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self, equity: float = 0.0) -> dict[str, Any]:
        pct = (self.total_usdt / equity * 100) if equity > 0 else 0.0
        return {
            "total_usdt": round(self.total_usdt, 2),
            "total_pct": round(pct, 2),
            "by_asset": {k: round(v, 2) for k, v in self.by_asset.items()},
            "by_direction": {k: round(v, 2) for k, v in self.by_direction.items()},
            "by_timeframe": {k: round(v, 2) for k, v in self.by_timeframe.items()},
            "by_strategy": {k: round(v, 2) for k, v in self.by_strategy.items()},
            "correlated_usdt": round(self.correlated_usdt, 2),
            "positions": self.positions,
        }


@dataclass
class PortfolioRiskDecision:
    approved: bool
    scale: float = 1.0
    reason: str = "approved"
    snapshot: ExposureSnapshot = field(default_factory=ExposureSnapshot)


def _asset(symbol: str) -> str:
    return str(symbol or "").split("/")[0].upper() or "UNKNOWN"


def _direction(side: Side | str | None) -> str:
    raw = getattr(side, "value", side) or "long"
    raw = str(raw).lower()
    if raw in {"short", "sell"}:
        return "short"
    return "long"


def _notional(position: Position, mark_price: float | None = None) -> float:
    price = mark_price or position.current_price or position.entry_price
    return max(float(price), 0.0) * max(float(position.quantity), 0.0)


def _is_correlated(asset: str, strategy: str, row: dict[str, Any]) -> bool:
    row_asset = str(row.get("asset") or "").upper()
    row_strategy = str(row.get("strategy") or "")
    if asset in {"BTC", "ETH"} and row_asset in {"BTC", "ETH"}:
        return True
    return bool(strategy and row_strategy and strategy == row_strategy)


def aggregate_exposure(*, exclude_slot: str | None = None) -> ExposureSnapshot:
    snapshot = ExposureSnapshot()
    try:
        from atlas.runtime.bot_runner import bot_pool
    except Exception:
        return snapshot

    for slot, engine in bot_pool.engines():
        if exclude_slot and slot == exclude_slot:
            continue
        position = getattr(engine, "_position", None)
        if position is None:
            try:
                position = engine.broker.get_position(engine.config.exchange.symbol)
            except Exception:
                position = None
        if position is None:
            continue
        symbol = position.symbol or engine.config.exchange.symbol
        asset = _asset(symbol)
        strategy = position.strategy or engine.config.strategy.name
        timeframe = engine.config.exchange.timeframe
        direction = _direction(position.side)
        notional = _notional(position)
        snapshot.total_usdt += notional
        snapshot.by_asset[asset] = snapshot.by_asset.get(asset, 0.0) + notional
        snapshot.by_direction[direction] = snapshot.by_direction.get(direction, 0.0) + notional
        snapshot.by_timeframe[timeframe] = snapshot.by_timeframe.get(timeframe, 0.0) + notional
        snapshot.by_strategy[strategy] = snapshot.by_strategy.get(strategy, 0.0) + notional
        snapshot.positions.append(
            {
                "slot": slot,
                "asset": asset,
                "symbol": symbol,
                "strategy": strategy,
                "timeframe": timeframe,
                "direction": direction,
                "notional": round(notional, 2),
            }
        )
    return snapshot


def evaluate_entry_risk(
    *,
    config: RiskConfig,
    equity: float,
    symbol: str,
    strategy: str,
    timeframe: str,
    side: Side | str,
    proposed_notional: float,
    slot: str | None = None,
) -> PortfolioRiskDecision:
    if equity <= 0 or proposed_notional <= 0:
        return PortfolioRiskDecision(False, 0.0, "invalid equity or notional")

    asset = _asset(symbol)
    direction = _direction(side)
    snapshot = aggregate_exposure(exclude_slot=slot)
    correlated = sum(row["notional"] for row in snapshot.positions if _is_correlated(asset, strategy, row))
    snapshot.correlated_usdt = correlated

    limits = [
        ("total exposure", snapshot.total_usdt, config.max_exposure_pct),
        (f"{asset} exposure", snapshot.by_asset.get(asset, 0.0), config.max_exposure_per_asset_pct),
        (f"{strategy} exposure", snapshot.by_strategy.get(strategy, 0.0), config.max_exposure_per_strategy_pct),
        (f"{direction} exposure", snapshot.by_direction.get(direction, 0.0), config.max_exposure_per_direction_pct),
        (f"{timeframe} exposure", snapshot.by_timeframe.get(timeframe, 0.0), config.max_exposure_per_timeframe_pct),
    ]

    scale = 1.0
    reasons: list[str] = []
    for label, current, limit_pct in limits:
        limit_usdt = max(float(limit_pct), 0.0) * equity
        remaining = limit_usdt - current
        if remaining <= 0:
            return PortfolioRiskDecision(False, 0.0, f"{label} limit reached", snapshot)
        if proposed_notional > remaining:
            scale = min(scale, remaining / proposed_notional)
            reasons.append(f"{label} scaled")

    if correlated / equity >= config.correlation_threshold:
        scale *= max(0.0, min(1.0, config.correlation_risk_scale))
        reasons.append("correlation risk scaled")

    if scale <= 0:
        return PortfolioRiskDecision(False, 0.0, "portfolio limits exhausted", snapshot)
    return PortfolioRiskDecision(True, min(1.0, scale), ", ".join(reasons) or "approved", snapshot)
