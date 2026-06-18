"""Contrato base dos módulos de entrada do QuantumTrend Pro."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from atlas.quantum.models import EntryModule, MultiTimeframeContext


@dataclass(frozen=True)
class SignalResult:
    """Resposta de um módulo de entrada — apenas oportunidade, sem risco/posição."""

    triggered: bool
    module: EntryModule
    confidence: float
    reason: str
    indicators: tuple[str, ...] = field(default_factory=tuple)

    @staticmethod
    def none(module: EntryModule, reason: str = "sem gatilho") -> SignalResult:
        return SignalResult(triggered=False, module=module, confidence=0.0, reason=reason)


class BaseEntryModule(ABC):
    """Módulo de entrada — avalia apenas o timeframe de execução dentro do contexto MTF."""

    name: EntryModule

    @abstractmethod
    def evaluate(self, ctx: MultiTimeframeContext) -> SignalResult:
        """Retorna se há oportunidade de entrada long neste candle."""
