from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from atlas.core.config import AtlasConfig, default_config_for_mode, default_paper_config, load_config
from atlas.core.symbols import OPERATED_BASES, base_from_symbol, build_symbol, validate_operated_base
from atlas.core.env import project_root
from atlas.core.models import TradingMode
from atlas.dashboard.strategy_config import (
    ACTIVE_CONFIG_REL,
    TIMEFRAMES,
    build_operational_config,
    list_strategy_names,
    save_config_yaml,
)
from atlas.strategies.mm200_trend_v2 import strategy_display_name

ACTIVE_PATH = project_root() / ACTIVE_CONFIG_REL
LIVE_PATH = project_root() / "config" / "live.yaml"
MAX_SLOTS_PER_BASE = 6
MAX_PAPER_SLOTS = MAX_SLOTS_PER_BASE * len(OPERATED_BASES)


def _slots_path() -> Path:
    return project_root() / "data" / "runtime" / "paper_slots.yaml"


@dataclass
class PaperSlot:
    strategy: str
    timeframe: str
    quote: str = "USDT"
    base: str = "BTC"
    enabled: bool = True


def slot_key(strategy: str, timeframe: str, base: str = "BTC") -> str:
    return f"{strategy}_{timeframe.lower()}_{base.lower()}"


def poll_seconds_for_timeframe(timeframe: str) -> int:
    tf = timeframe.lower()
    if tf == "1d":
        return 3600
    if tf == "1h":
        return 15
    return 30


def _empty_slot(base: str, *, strategy: str = "pullback_ema20_v1") -> PaperSlot:
    return PaperSlot(
        strategy=strategy,
        timeframe="4h",
        quote="USDT",
        base=validate_operated_base(base),
        enabled=False,
    )


def _normalize_paper_slots(slots: list[PaperSlot]) -> list[PaperSlot]:
    """Garante ordem estável: 6 slots BTC + 6 slots ETH."""
    if len(slots) >= MAX_PAPER_SLOTS:
        out: list[PaperSlot] = []
        for global_idx, slot in enumerate(slots[:MAX_PAPER_SLOTS]):
            base = OPERATED_BASES[0] if global_idx < MAX_SLOTS_PER_BASE else OPERATED_BASES[1]
            out.append(
                PaperSlot(
                    strategy=slot.strategy,
                    timeframe=slot.timeframe.lower(),
                    quote=slot.quote.upper(),
                    base=base,
                    enabled=slot.enabled,
                )
            )
        return out

    by_base: dict[str, list[PaperSlot]] = {base: [] for base in OPERATED_BASES}
    for slot in slots:
        base = validate_operated_base(slot.base)
        if len(by_base[base]) >= MAX_SLOTS_PER_BASE:
            continue
        by_base[base].append(
            PaperSlot(
                strategy=slot.strategy,
                timeframe=slot.timeframe.lower(),
                quote=slot.quote.upper(),
                base=base,
                enabled=slot.enabled,
            )
        )

    out = []
    for base in OPERATED_BASES:
        rows = by_base[base]
        while len(rows) < MAX_SLOTS_PER_BASE:
            rows.append(_empty_slot(base))
        out.extend(rows[:MAX_SLOTS_PER_BASE])
    return out[:MAX_PAPER_SLOTS]


def _default_slots_from_active() -> list[PaperSlot]:
    cfg = load_active_paper_config()
    primary = PaperSlot(
        strategy=cfg.strategy.name,
        timeframe=cfg.exchange.timeframe,
        quote=cfg.exchange.symbol.split("/")[-1],
        base=base_from_symbol(cfg.exchange.symbol),
        enabled=True,
    )
    return _normalize_paper_slots([primary])


def load_paper_slots() -> list[PaperSlot]:
    path = _slots_path()
    if not path.is_file():
        return _default_slots_from_active()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = raw.get("slots") or []
    out: list[PaperSlot] = []
    for row in rows[:MAX_PAPER_SLOTS]:
        if not isinstance(row, dict):
            continue
        out.append(
            PaperSlot(
                strategy=str(row.get("strategy", "mm200_trend_v2")),
                timeframe=str(row.get("timeframe", "4h")).lower(),
                quote=str(row.get("quote", "USDT")).upper(),
                base=str(row.get("base", "BTC")).upper(),
                enabled=bool(row.get("enabled", True)),
            )
        )
    if not out:
        return _default_slots_from_active()
    return _normalize_paper_slots(out)


def _validate_slots(slots: list[PaperSlot]) -> None:
    if len(slots) > MAX_PAPER_SLOTS:
        raise ValueError(f"Máximo {MAX_PAPER_SLOTS} slots")
    enabled = [s for s in slots if s.enabled]
    if len(enabled) > MAX_PAPER_SLOTS:
        raise ValueError(f"Máximo {MAX_PAPER_SLOTS} estratégias habilitadas ao mesmo tempo")
    for base in OPERATED_BASES:
        per_base = sum(1 for s in enabled if s.base.upper() == base)
        if per_base > MAX_SLOTS_PER_BASE:
            raise ValueError(f"Máximo {MAX_SLOTS_PER_BASE} estratégias habilitadas em {base}")
    keys = [slot_key(s.strategy, s.timeframe, s.base) for s in enabled]
    if len(keys) != len(set(keys)):
        raise ValueError("Combinação estratégia + timeframe + ativo duplicada")
    from atlas.strategies.market_orchestrator import validate_slot_market_mix

    validate_slot_market_mix([s for s in slots if s.enabled])
    root = project_root()
    for s in slots:
        if s.enabled and s.strategy not in list_strategy_names(root):
            raise ValueError(f"Estratégia desconhecida: {s.strategy}")
        if s.timeframe.lower() not in TIMEFRAMES:
            raise ValueError(f"Timeframe inválido: {s.timeframe}. Use 1h, 4h ou 1d.")
        validate_operated_base(s.base)


def save_paper_slots(slots: list[PaperSlot]) -> list[PaperSlot]:
    slots = _normalize_paper_slots(slots)
    _validate_slots(slots)
    path = _slots_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "max_slots": MAX_PAPER_SLOTS,
        "max_slots_per_base": MAX_SLOTS_PER_BASE,
        "slots": [
            {
                "strategy": s.strategy,
                "timeframe": s.timeframe.lower(),
                "quote": s.quote.upper(),
                "base": s.base.upper(),
                "enabled": s.enabled,
            }
            for s in slots[:MAX_PAPER_SLOTS]
        ],
    }
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    enabled = [s for s in slots if s.enabled]
    if enabled:
        primary = enabled[0]
        cfg = build_operational_config(
            project_root(),
            strategy_name=primary.strategy,
            quote_asset=primary.quote,
            base_asset=primary.base,
            timeframe=primary.timeframe.lower(),
        )
        cfg.runtime.poll_seconds = poll_seconds_for_timeframe(primary.timeframe)
        save_config_yaml(ACTIVE_PATH, cfg)
        _sync_live_yaml(cfg)
    return slots[:MAX_PAPER_SLOTS]


def build_config_for_slot(slot: PaperSlot) -> AtlasConfig:
    cfg = build_operational_config(
        project_root(),
        strategy_name=slot.strategy,
        quote_asset=slot.quote,
        base_asset=slot.base,
        timeframe=slot.timeframe.lower(),
    )
    cfg.runtime.poll_seconds = poll_seconds_for_timeframe(slot.timeframe)
    return cfg


def enabled_paper_configs() -> list[tuple[str, AtlasConfig]]:
    configs: list[tuple[str, AtlasConfig]] = []
    for slot in load_paper_slots():
        if not slot.enabled:
            continue
        key = slot_key(slot.strategy, slot.timeframe, slot.base)
        configs.append((key, build_config_for_slot(slot)))
    return configs


def load_active_paper_config() -> AtlasConfig:
    if ACTIVE_PATH.is_file():
        return load_config(ACTIVE_PATH)
    cfg = default_paper_config()
    cfg.runtime.poll_seconds = poll_seconds_for_timeframe(cfg.exchange.timeframe)
    return cfg


def _sync_live_yaml(cfg: AtlasConfig) -> None:
    """Mantém live.yaml alinhado com estratégia/timeframe selecionados."""
    if not LIVE_PATH.is_file():
        return
    live = load_config(LIVE_PATH)
    live.exchange.symbol = cfg.exchange.symbol
    live.exchange.timeframe = cfg.exchange.timeframe
    live.strategy = cfg.strategy
    live.runtime.poll_seconds = poll_seconds_for_timeframe(cfg.exchange.timeframe)
    data = live.model_dump(mode="json")
    with LIVE_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def resolve_active_config(*, live_running: bool = False) -> AtlasConfig:
    if live_running:
        live = default_config_for_mode(TradingMode.LIVE)
        if ACTIVE_PATH.is_file():
            active = load_config(ACTIVE_PATH)
            live.exchange.symbol = active.exchange.symbol
            live.exchange.timeframe = active.exchange.timeframe
            live.strategy = active.strategy
            live.runtime.poll_seconds = poll_seconds_for_timeframe(active.exchange.timeframe)
        return live
    return load_active_paper_config()


def save_operational_selection(
    *,
    strategy_name: str,
    timeframe: str = "4h",
    quote_asset: str = "USDT",
    base_asset: str = "BTC",
) -> AtlasConfig:
    tf = timeframe.lower()
    if tf not in TIMEFRAMES:
        raise ValueError(f"Timeframe inválido: {timeframe}. Use 1h, 4h ou 1d.")

    root = project_root()
    if strategy_name not in list_strategy_names(root):
        raise ValueError(f"Estratégia desconhecida: {strategy_name}")

    base = validate_operated_base(base_asset)
    slots = load_paper_slots()
    primary = PaperSlot(
        strategy=strategy_name,
        timeframe=tf,
        quote=quote_asset,
        base=base,
        enabled=True,
    )
    base_indices = [i for i, s in enumerate(slots) if s.base.upper() == base]
    if base_indices:
        slots[base_indices[0]] = primary
    else:
        offset = 0 if base == "BTC" else MAX_SLOTS_PER_BASE
        slots[offset] = primary
    save_paper_slots(slots)
    return build_config_for_slot(primary)


def operational_options() -> dict:
    root = project_root()
    cfg = load_active_paper_config()
    names = list_strategy_names(root)
    slots = load_paper_slots()
    return {
        "strategies": [
            {"id": n, "name": strategy_display_name(n)} for n in names
        ],
        "timeframes": list(TIMEFRAMES),
        "quotes": ["USDT", "USDC"],
        "bases": list(OPERATED_BASES),
        "max_slots": MAX_PAPER_SLOTS,
        "max_slots_per_base": MAX_SLOTS_PER_BASE,
        "slots": [
            {
                "strategy": s.strategy,
                "strategy_label": strategy_display_name(s.strategy),
                "timeframe": s.timeframe,
                "quote": s.quote,
                "base": s.base,
                "symbol": build_symbol(s.base, s.quote),
                "enabled": s.enabled,
                "key": slot_key(s.strategy, s.timeframe, s.base),
            }
            for s in slots
        ],
        "active": {
            "strategy": cfg.strategy.name,
            "strategy_label": strategy_display_name(cfg.strategy.name),
            "timeframe": cfg.exchange.timeframe,
            "symbol": cfg.exchange.symbol,
            "quote": cfg.exchange.symbol.split("/")[-1],
            "poll_seconds": cfg.runtime.poll_seconds,
        },
    }
