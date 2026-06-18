"""Decision Engine — orquestra módulos de entrada e seleciona o melhor sinal."""
from __future__ import annotations

from dataclasses import dataclass, field

from atlas.core.models import Signal, SignalAction
from atlas.quantum.entry_modules import ENTRY_MODULE_BY_NAME, ENTRY_MODULE_INSTANCES, get_entry_module
from atlas.quantum.entry_modules.base_entry_module import SignalResult
from atlas.quantum.models import EntryModule, MultiTimeframeContext


@dataclass(frozen=True)
class EntryDecision:
    """Sinal de entrada selecionado pelo core."""

    module: EntryModule
    signal: Signal
    confidence: float
    reason: str
    indicators: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DecisionResult:
    selected: EntryDecision | None
    evaluations: tuple[SignalResult, ...]
    rejected: tuple[dict[str, object], ...] = field(default_factory=tuple)


class DecisionEngine:
    """
    Executa módulos de entrada e seleciona o sinal com maior confidence.
    Não recalcula regime, alignment ou risco — apenas identifica oportunidades.
    """

    def evaluate(self, ctx: MultiTimeframeContext, mode: EntryModule = EntryModule.AUTO) -> DecisionResult:
        modules = self._modules_for_mode(mode)
        evaluations = tuple(mod.evaluate(ctx) for mod in modules)
        triggered = [r for r in evaluations if r.triggered]

        if not triggered:
            return DecisionResult(selected=None, evaluations=evaluations)

        best = max(triggered, key=lambda r: r.confidence)
        rejected: list[dict[str, object]] = []
        for candidate in triggered:
            if candidate.module == best.module:
                continue
            rejected.append(
                {
                    "module": candidate.module.value,
                    "confidence": candidate.confidence,
                    "reason": candidate.reason,
                    "status": "detectado_nao_executado",
                    "detail": f"Score inferior ao {best.module.value} ({candidate.confidence:.0f} < {best.confidence:.0f}).",
                }
            )

        signal = Signal(
            action=SignalAction.ENTER_LONG,
            reason=best.reason,
            metadata={
                "entry_module": best.module.value,
                "entry_confidence": best.confidence,
                "entry_indicators": list(best.indicators),
                "rejected_modules": rejected,
            },
        )
        decision = EntryDecision(
            module=best.module,
            signal=signal,
            confidence=best.confidence,
            reason=best.reason,
            indicators=best.indicators,
        )
        return DecisionResult(selected=decision, evaluations=evaluations, rejected=tuple(rejected))

    @staticmethod
    def _modules_for_mode(mode: EntryModule):
        if mode == EntryModule.AUTO:
            return ENTRY_MODULE_INSTANCES
        handler = get_entry_module(mode)
        return (handler,) if handler is not None else ENTRY_MODULE_INSTANCES

    @staticmethod
    def module_status(evaluations: tuple[SignalResult, ...]) -> dict[str, dict[str, object]]:
        """Status dos módulos para dashboard (Ativo / sem sinal)."""
        out: dict[str, dict[str, object]] = {}
        for result in evaluations:
            out[result.module.value] = {
                "active": True,
                "triggered": result.triggered,
                "confidence": result.confidence if result.triggered else None,
                "reason": result.reason,
            }
        for mod in ENTRY_MODULE_BY_NAME:
            out.setdefault(mod.value, {"active": True, "triggered": False, "confidence": None, "reason": "sem gatilho"})
        return out
