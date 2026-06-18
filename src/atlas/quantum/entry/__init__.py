"""Módulos de entrada — compatibilidade + reexport do Decision Engine."""
from __future__ import annotations

from atlas.quantum.decision_engine import DecisionEngine, EntryDecision
from atlas.quantum.models import EntryModule, MultiTimeframeContext

# Compatibilidade com imports antigos
EntrySignal = EntryDecision


def evaluate_entry(ctx: MultiTimeframeContext, module: EntryModule) -> EntryDecision | None:
    """API legada — delega ao Decision Engine."""
    result = DecisionEngine().evaluate(ctx, module)
    return result.selected


__all__ = ["DecisionEngine", "EntryDecision", "EntrySignal", "evaluate_entry"]
