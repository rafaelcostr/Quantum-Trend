"""Módulos de entrada internos do QuantumTrend Pro Core."""
from __future__ import annotations

from atlas.quantum.entry_modules.base_entry_module import BaseEntryModule, SignalResult
from atlas.quantum.entry_modules.breakout_module import BreakoutModule
from atlas.quantum.entry_modules.pullback_module import PullbackModule
from atlas.quantum.entry_modules.supertrend_module import SupertrendModule
from atlas.quantum.models import EntryModule

ENTRY_MODULE_INSTANCES: tuple[BaseEntryModule, ...] = (
    PullbackModule(),
    BreakoutModule(),
    SupertrendModule(),
)

ENTRY_MODULE_BY_NAME: dict[EntryModule, BaseEntryModule] = {
    mod.name: mod for mod in ENTRY_MODULE_INSTANCES if mod.name != EntryModule.AUTO
}


def list_entry_modules() -> list[EntryModule]:
    return [mod.name for mod in ENTRY_MODULE_INSTANCES]


def get_entry_module(name: EntryModule) -> BaseEntryModule | None:
    return ENTRY_MODULE_BY_NAME.get(name)


__all__ = [
    "BaseEntryModule",
    "BreakoutModule",
    "ENTRY_MODULE_BY_NAME",
    "ENTRY_MODULE_INSTANCES",
    "PullbackModule",
    "SignalResult",
    "SupertrendModule",
    "get_entry_module",
    "list_entry_modules",
]
