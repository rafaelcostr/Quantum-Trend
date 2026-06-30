from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from atlas.brokers.binance import asset_color, fetch_account_snapshot, fetch_last_price
from atlas.core.config import default_config_for_mode
from atlas.core.env import get_settings
from atlas.core.models import PositionDTO, Side, TradingMode
from atlas.monitoring.alerts import get_alerts
from atlas.runtime.bot_runner import bot_pool
from atlas.runtime.live_gates import evaluate_live_gates
from atlas.core.symbols import base_from_symbol
from atlas.runtime.operational_config import enabled_paper_configs, resolve_active_config, slot_key
from atlas.runtime.operational_safety import evaluate_scoped_kill_switch
from atlas.services.demo_account import entry_price_from_event, mark_price, open_entry_from_journal
from atlas.strategies.mm200_trend_v2 import strategy_display_name

_POSITIONS_CACHE: list[PositionDTO] | None = None
_POSITIONS_CACHE_AT: float = 0.0
_POSITIONS_TTL = 10.0


@dataclass
class BotState:
    running: bool = False
    mode: TradingMode = TradingMode.PAPER
    started_at: datetime | None = None
    strategy: str = "mm200_trend_v2"
    performance_30d_pct: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _start(self, mode: TradingMode) -> None:
        settings = get_settings()
        if settings.kill_switch_active:
            raise RuntimeError("Kill switch global ativo — bot bloqueado")
        if bot_pool.is_alive() and bot_pool.mode != mode:
            raise RuntimeError(
                f"Bot já rodando em modo {bot_pool.mode.value if bot_pool.mode else '?'} — pare antes"
            )

        if mode == TradingMode.LIVE:
            cfg = resolve_active_config(live_running=True)
            configs = [
                (
                    slot_key(
                        cfg.strategy.name,
                        cfg.exchange.timeframe,
                        base_from_symbol(cfg.exchange.symbol),
                    ),
                    cfg,
                )
            ]
        else:
            configs = enabled_paper_configs()
            if not configs:
                raise RuntimeError(
                    "Nenhuma estratégia habilitada — configure até 6 em Estratégias (4H e/ou 1D)"
                )

        for _, cfg in configs:
            kill = evaluate_scoped_kill_switch(
                global_active=settings.kill_switch_active,
                symbol=cfg.exchange.symbol,
                strategy=cfg.strategy.name,
            )
            if kill.blocked:
                raise RuntimeError(kill.reason or "Kill switch ativo — bot bloqueado")

        bot_pool.start_all(mode=mode, configs=configs)
        primary = configs[0][1]
        self.strategy = primary.strategy.name
        self.mode = mode
        self.running = True
        self.started_at = datetime.now(timezone.utc)
        mode_label = "Paper (Binance Demo)" if mode == TradingMode.PAPER else "Live (Binance Real)"
        if len(configs) == 1:
            label = strategy_display_name(primary.strategy.name)
        else:
            label = f"{len(configs)} estratégias"
        get_alerts().notify_bot_started(
            strategy=label,
            symbol=primary.exchange.symbol,
            mode=mode_label,
        )

    def start_paper(self) -> None:
        with self._lock:
            if bot_pool.is_alive() and self.mode == TradingMode.LIVE:
                raise RuntimeError("Bot live ativo — pare o live antes de iniciar paper")
            self._start(TradingMode.PAPER)

    def start_live(self) -> None:
        with self._lock:
            gates = evaluate_live_gates()
            if not gates["eligible"]:
                reasons = "; ".join(gates["blocking_reasons"][:3])
                extra = f" (+{len(gates['blocking_reasons']) - 3})" if len(gates["blocking_reasons"]) > 3 else ""
                raise RuntimeError(f"Gates live não atendidos: {reasons}{extra}")
            self._start(TradingMode.LIVE)

    def start(self) -> None:
        """Compat: inicia paper."""
        self.start_paper()

    def stop(self) -> None:
        with self._lock:
            strategy = strategy_display_name(self.strategy)
            mode_label = self.mode.value
            self.running = False
        bot_pool.stop_all()
        get_alerts().notify_bot_stopped(strategy=strategy, mode=mode_label)

    def snapshot(self) -> dict:
        with self._lock:
            instances = bot_pool.snapshot_instances()
            primary_engine = bot_pool.engine
            days = 0
            if self.started_at:
                days = max(0, (datetime.now(timezone.utc) - self.started_at).days)
            total_ticks = sum(i.get("ticks", 0) for i in instances)
            errors = [i["last_error"] for i in instances if i.get("last_error")]
            return {
                "running": self.running and bot_pool.is_alive(),
                "mode": self.mode.value,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "strategy": self.strategy,
                "performance_30d_pct": self.performance_30d_pct,
                "days_running": days,
                "ticks": total_ticks,
                "last_tick_at": primary_engine.last_tick_at.isoformat()
                if primary_engine and primary_engine.last_tick_at
                else None,
                "last_error": errors[0] if errors else None,
                "in_position": any(i.get("in_position") for i in instances),
                "engine_alive": bot_pool.is_alive(),
                "instance_count": len(instances),
                "instances": instances,
            }


bot_state = BotState()


def active_config():
    """Config operacional ativa (runtime ou paper.yaml)."""
    return resolve_active_config(live_running=bot_state.running and bot_state.mode == TradingMode.LIVE)


def _position_from_engine(engine, cfg, *, current: float | None = None) -> PositionDTO | None:
    symbol = cfg.exchange.symbol
    base = symbol.split("/")[0]
    mark = current if current is not None else mark_price(symbol)
    if engine and engine._position:
        pos = engine._position
        pos.current_price = mark or pos.entry_price
        return PositionDTO(
            asset=base,
            side="LONG",
            entry=round(pos.entry_price, 4),
            current=round(pos.current_price, 4),
            pnl=round(pos.pnl, 2),
            pnl_pct=round(pos.pnl_pct, 2),
            strategy=strategy_display_name(cfg.strategy.name),
            color=asset_color(base),
        )
    return None


def build_positions() -> list[PositionDTO]:
    global _POSITIONS_CACHE, _POSITIONS_CACHE_AT
    now = time.time()
    if _POSITIONS_CACHE is not None and (now - _POSITIONS_CACHE_AT) < _POSITIONS_TTL:
        return _POSITIONS_CACHE

    cfg = active_config()
    symbol = cfg.exchange.symbol
    base = symbol.split("/")[0]
    live = bot_state.mode == TradingMode.LIVE and bot_state.running
    mode = bot_state.mode if bot_state.running else TradingMode.PAPER

    if bot_pool.is_alive():
        positions: list[PositionDTO] = []
        current = mark_price(symbol)
        for _key, engine in bot_pool.engines():
            pos = _position_from_engine(engine, engine.config, current=current)
            if pos:
                positions.append(pos)
        if positions:
            _POSITIONS_CACHE = positions
            _POSITIONS_CACHE_AT = now
            return positions

    current = mark_price(symbol)
    snap = fetch_account_snapshot(symbol, live=live)
    if snap and snap.base_total > 0.00001 and current > 0:
        qty = snap.base_total
        open_ev = open_entry_from_journal(mode=mode, symbol=symbol)
        entry = entry_price_from_event(open_ev) if open_ev else None
        if entry is None:
            _POSITIONS_CACHE = []
            _POSITIONS_CACHE_AT = now
            return []
        pnl = (current - entry) * qty
        positions = [
            PositionDTO(
                asset=base,
                side="LONG",
                entry=round(entry, 4),
                current=round(current, 4),
                pnl=round(pnl, 2),
                pnl_pct=round((current / entry - 1) * 100 if entry else 0, 2),
                strategy=strategy_display_name(cfg.strategy.name),
                color=asset_color(base),
            )
        ]
        _POSITIONS_CACHE = positions
        _POSITIONS_CACHE_AT = now
        return positions
    _POSITIONS_CACHE = []
    _POSITIONS_CACHE_AT = now
    return []
