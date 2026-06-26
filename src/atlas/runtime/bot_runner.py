from __future__ import annotations

import threading

from atlas.core.config import AtlasConfig, default_config_for_mode
from atlas.core.log import log_event, logger
from atlas.core.models import TradingMode
from atlas.runtime.engine import TradingEngine
from atlas.runtime.risk_store import apply_risk_to_engine
from atlas.services.balance_history import record_balance
from atlas.strategies.mm200_trend_v2 import strategy_display_name

from atlas.runtime.operational_config import MAX_PAPER_SLOTS

MAX_PARALLEL_SLOTS = MAX_PAPER_SLOTS


class BotRunner:
    """Executa um TradingEngine em thread daemon."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._engine: TradingEngine | None = None
        self._mode: TradingMode | None = None
        self.slot_key: str = ""

    def start(
        self,
        *,
        mode: TradingMode = TradingMode.PAPER,
        config: AtlasConfig | None = None,
        slot_key: str = "",
    ) -> None:
        if self._thread and self._thread.is_alive():
            if self._mode == mode:
                return
            raise RuntimeError(f"Runner {slot_key or '?'} já ativo em modo {self._mode}")

        cfg = config or default_config_for_mode(mode)
        cfg.mode = mode
        self.slot_key = slot_key or f"{cfg.strategy.name}_{cfg.exchange.timeframe}"
        self._engine = TradingEngine(cfg)
        apply_risk_to_engine(self._engine)
        self._mode = mode
        self._engine.journal.log(
            "runner_start",
            cfg.exchange.symbol,
            strategy=cfg.strategy.name,
            timeframe=cfg.exchange.timeframe,
            mode=cfg.mode.value,
            slot=self.slot_key,
        )
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name=f"atlas-bot-{self.slot_key}",
            daemon=True,
        )
        self._thread.start()
        log_event(
            20,
            "bot_runner.started",
            module="runtime.bot_runner",
            slot=self.slot_key,
            strategy=cfg.strategy.name,
            timeframe=cfg.exchange.timeframe,
            symbol=cfg.exchange.symbol,
            mode=cfg.mode.value,
        )
        logger.info(
            "Bot runner iniciado (%s, %s · %s)",
            cfg.mode.value,
            cfg.strategy.name,
            cfg.exchange.timeframe,
        )

    def stop(self) -> None:
        slot = self.slot_key
        engine = self._engine
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=8)
        log_event(
            20,
            "bot_runner.stopped",
            module="runtime.bot_runner",
            slot=slot,
            strategy=engine.config.strategy.name if engine else None,
            timeframe=engine.config.exchange.timeframe if engine else None,
            symbol=engine.config.exchange.symbol if engine else None,
            mode=engine.config.mode.value if engine else None,
        )
        self._thread = None
        self._engine = None
        self._mode = None
        self.slot_key = ""

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def mode(self) -> TradingMode | None:
        return self._mode

    @property
    def engine(self) -> TradingEngine | None:
        return self._engine

    def _loop(self) -> None:
        engine = self._engine
        if engine is None:
            logger.warning("Runner %s iniciado sem engine; encerrando thread", self.slot_key or "?")
            return
        poll = engine.config.runtime.poll_seconds
        while not self._stop.is_set():
            try:
                apply_risk_to_engine(engine)
                outcome = engine.process_once()
                outcome["slot"] = self.slot_key
                outcome["strategy"] = engine.config.strategy.name
                outcome["timeframe"] = engine.config.exchange.timeframe
                engine.journal.log("tick", engine.config.exchange.symbol, **outcome)
                from atlas.platform.orchestrator import platform_orchestrator

                platform_orchestrator.post_tick(engine, outcome)
                equity = outcome.get("equity")
                if isinstance(equity, (int, float)) and equity > 0:
                    record_balance(
                        mode=engine.config.mode,
                        equity=float(equity),
                        symbol=engine.config.exchange.symbol,
                    )
            except Exception as exc:
                engine.last_error = str(exc)
                engine.journal.log(
                    "error",
                    engine.config.exchange.symbol,
                    error=str(exc),
                    slot=self.slot_key,
                )
                from atlas.platform.orchestrator import platform_orchestrator

                platform_orchestrator.on_error(engine, str(exc))
                log_event(
                    40,
                    "bot_runner.tick.failed",
                    module="runtime.bot_runner",
                    slot=self.slot_key,
                    strategy=engine.config.strategy.name,
                    timeframe=engine.config.exchange.timeframe,
                    symbol=engine.config.exchange.symbol,
                    mode=engine.config.mode.value,
                    error=str(exc)[:240],
                )
                logger.exception("Erro no tick (%s): %s", self.slot_key, exc)
            self._stop.wait(poll)


class BotRunnerPool:
    """Gerencia até 12 engines paper/live em paralelo (6 por moeda)."""

    def __init__(self) -> None:
        self._runners: dict[str, BotRunner] = {}
        self._mode: TradingMode | None = None
        self._lock = threading.Lock()

    def start_all(self, *, mode: TradingMode, configs: list[tuple[str, AtlasConfig]]) -> None:
        if not configs:
            raise RuntimeError("Nenhuma estratégia habilitada")
        if len(configs) > MAX_PARALLEL_SLOTS:
            raise RuntimeError(f"Máximo {MAX_PARALLEL_SLOTS} estratégias simultâneas")

        with self._lock:
            if self._runners and self._mode != mode:
                raise RuntimeError(
                    f"Bot já rodando em modo {self._mode.value if self._mode else '?'} — pare antes"
                )
            self._stop_all_unlocked()
            for key, cfg in configs:
                runner = BotRunner()
                runner.start(mode=mode, config=cfg, slot_key=key)
                self._runners[key] = runner
            self._mode = mode

    def _stop_all_unlocked(self) -> None:
        for runner in list(self._runners.values()):
            runner.stop()
        self._runners.clear()
        self._mode = None

    def stop_all(self) -> None:
        with self._lock:
            self._stop_all_unlocked()

    def stop(self) -> None:
        """Alias compatível com bot_runner legado."""
        self.stop_all()

    def is_alive(self) -> bool:
        return any(r.is_alive() for r in self._runners.values())

    @property
    def mode(self) -> TradingMode | None:
        return self._mode

    @property
    def engine(self) -> TradingEngine | None:
        for runner in self._runners.values():
            if runner.engine:
                return runner.engine
        return None

    def engines(self) -> list[tuple[str, TradingEngine]]:
        return [(k, r.engine) for k, r in self._runners.items() if r.engine]

    def snapshot_instances(self) -> list[dict]:
        out: list[dict] = []
        for key, runner in self._runners.items():
            eng = runner.engine
            if not eng:
                continue
            strategy = eng.config.strategy.name
            out.append(
                {
                    "key": key,
                    "strategy": strategy,
                    "strategy_label": strategy_display_name(strategy),
                    "timeframe": eng.config.exchange.timeframe,
                    "symbol": eng.config.exchange.symbol,
                    "ticks": eng.ticks,
                    "last_tick_at": eng.last_tick_at.isoformat() if eng.last_tick_at else None,
                    "last_error": eng.last_error,
                    "in_position": eng._position is not None,
                    "poll_seconds": eng.config.runtime.poll_seconds,
                    "alive": runner.is_alive(),
                }
            )
        return out


bot_pool = BotRunnerPool()
# Compat legado
bot_runner = bot_pool
