"""QuantumTrend Pro Core — orquestra regime, score e entradas."""
from __future__ import annotations

from typing import Any

import pandas as pd

from atlas.core.models import Candle, IndicatorSnapshot, Position, Signal, SignalAction
from atlas.quantum.alignment import AlignmentScoreEngine
from atlas.quantum.decision_engine import DecisionEngine
from atlas.quantum.models import EntryModule, REGIME_LABELS, RiskProfile
from atlas.quantum.multi_timeframe import MultiTimeframeEngine
from atlas.quantum.position_manager import PositionManager
from atlas.quantum.regime import MarketRegimeEngine


class QuantumTrendProStrategy:
    """
    Estratégia principal do TradeBot Pro.
    Execução no 1H com filtros 1D + 4H + Alignment Score + Entry Modules.
    """

    name = "quantum_trend_pro"
    uses_multi_timeframe = True

    def __init__(
        self,
        *,
        entry_module: str = "auto",
        risk_profile: str = "moderate",
        stop_atr: float = 1.0,
        target_atr: float = 2.0,
    ) -> None:
        self.entry_module = EntryModule(entry_module)
        self.risk_profile = RiskProfile(risk_profile)
        self.regime_engine = MarketRegimeEngine()
        self.alignment_engine = AlignmentScoreEngine(risk_profile=self.risk_profile)
        self.position_manager = PositionManager(stop_atr=stop_atr, target_atr=target_atr)
        self.mtf_engine = MultiTimeframeEngine()
        self.decision_engine = DecisionEngine()
        self._last_context: dict[str, Any] = {}
        self._last_decision: dict[str, Any] = {}

    def build_context(self, row: pd.Series, candle: Candle):
        ctx = self.mtf_engine.context_from_row(row, candle)
        regime_result = self.regime_engine.classify(ctx)
        ctx.regime = regime_result.regime
        ctx.meta = {
            "regime_label": REGIME_LABELS[regime_result.regime],
            "regime_reason": regime_result.reason,
        }
        return ctx

    def evaluate_context(self, ctx, position: Position | None) -> Signal:
        if position is not None:
            atr = ctx.atr_execution or 0.0
            exit_signal = self.position_manager.evaluate_exit(position, ctx.execution.candle, atr)
            if exit_signal:
                exit_signal.metadata.update(self._context_metadata(ctx))
                return exit_signal
            return Signal(action=SignalAction.HOLD, reason="posição em monitoramento", metadata=self._context_metadata(ctx))

        if not self.regime_engine.allows_long(ctx.regime):
            return Signal(
                action=SignalAction.HOLD,
                reason=f"regime não operável: {REGIME_LABELS[ctx.regime]}",
                metadata=self._context_metadata(ctx),
            )

        if not ctx.macro_bull:
            return Signal(action=SignalAction.HOLD, reason="1D não confirma tendência de alta", metadata=self._context_metadata(ctx))

        if not ctx.confirm_bull:
            return Signal(action=SignalAction.HOLD, reason="4H contrário ou sem confirmação", metadata=self._context_metadata(ctx))

        decision = self.decision_engine.evaluate(ctx, self.entry_module)
        self._last_decision = {
            "module_status": DecisionEngine.module_status(decision.evaluations),
            "evaluations": [
                {
                    "module": r.module.value,
                    "triggered": r.triggered,
                    "confidence": r.confidence,
                    "reason": r.reason,
                }
                for r in decision.evaluations
            ],
            "rejected_modules": list(decision.rejected),
            "selected_module": decision.selected.module.value if decision.selected else None,
            "selected_confidence": decision.selected.confidence if decision.selected else None,
        }

        entry_signal = decision.selected is not None
        alignment = self.alignment_engine.score(ctx, entry_signal=entry_signal)
        ctx.alignment_score = alignment.total
        ctx.alignment_breakdown = alignment.breakdown

        if decision.selected is None:
            return Signal(
                action=SignalAction.HOLD,
                reason="nenhum gatilho 1H",
                metadata=self._context_metadata(ctx, alignment),
            )

        if not alignment.eligible:
            return Signal(
                action=SignalAction.HOLD,
                reason=f"alignment score {alignment.total} < {alignment.threshold}",
                metadata=self._context_metadata(ctx, alignment, decision.selected),
            )

        atr = ctx.atr_execution or 0.0
        entry_price = ctx.execution.candle.close
        levels = self.position_manager.levels_for_entry(entry_price, atr)
        meta = self._context_metadata(ctx, alignment, decision.selected)
        meta.update(decision.selected.signal.metadata or {})
        return Signal(
            action=SignalAction.ENTER_LONG,
            reason=decision.selected.reason,
            stop_price=levels.stop_price,
            target_price=levels.target_price,
            metadata=meta,
        )

    def evaluate(
        self,
        candle: Candle,
        indicators: IndicatorSnapshot,
        position: Position | None,
    ) -> Signal:
        """Compatibilidade com TradingEngine — usa contexto pré-montado quando disponível."""
        row = indicators.extra.get("_quantum_row")
        if row is None:
            return Signal(action=SignalAction.HOLD, reason="contexto multi-timeframe ausente")
        ctx = self.build_context(row, candle)
        return self.evaluate_context(ctx, position)

    def last_decision_snapshot(self) -> dict[str, Any]:
        return dict(self._last_decision)

    def _context_metadata(self, ctx, alignment=None, entry: Any | None = None) -> dict[str, Any]:
        payload = {
            "regime": ctx.regime.value,
            "regime_label": ctx.meta.get("regime_label"),
            "alignment_score": ctx.alignment_score,
            "alignment_breakdown": ctx.alignment_breakdown,
            "macro_bull": ctx.macro_bull,
            "confirm_bull": ctx.confirm_bull,
            "entry_module": entry.module.value if entry else self.entry_module.value,
            "entry_confidence": getattr(entry, "confidence", None),
            "entry_indicators": list(getattr(entry, "indicators", ()) or ()),
            "risk_profile": self.risk_profile.value,
            "module_status": self._last_decision.get("module_status"),
            "rejected_modules": self._last_decision.get("rejected_modules"),
        }
        if alignment is not None:
            payload["alignment_threshold"] = alignment.threshold
        self._last_context = payload
        return payload


def build_quantum_trend_pro(params: dict) -> QuantumTrendProStrategy:
    return QuantumTrendProStrategy(
        entry_module=str(params.get("entry_module", "auto")),
        risk_profile=str(params.get("risk_profile", "moderate")),
        stop_atr=float(params.get("stop_atr", 1.0)),
        target_atr=float(params.get("target_atr", 2.0)),
    )
