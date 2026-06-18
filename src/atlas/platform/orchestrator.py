"""Orquestrador da plataforma — integra recovery, qualidade, decisões e gates."""
from __future__ import annotations

from typing import Any

from atlas.core.models import SignalAction, TradingMode
from atlas.platform.alerts import (
    alert_data_quality,
    alert_health_drop,
    alert_high_score,
    alert_recovery_required,
    alert_regime_change,
    alert_sync_failure,
    alert_trade_open,
)
from atlas.platform.capital_scaling import apply_capital_scaling
from atlas.platform.data_quality import assess_dataframe
from atlas.platform.decisions import record_decision
from atlas.platform.engine_monitor import collect_engine_metrics
from atlas.platform.models import PlatformState
from atlas.platform.recovery import run_position_recovery
from atlas.platform.score_explanation import build_score_explanation, persist_score_explanation
from atlas.platform.state_machine import can_execute_event, sync_state_from_runtime, transition
from atlas.platform.store import is_risk_locked, load_platform_state, patch_platform_state
from atlas.platform.trend_exhaustion import detect_trend_exhaustion
from atlas.runtime.reconciler import PositionReconciler


class PlatformOrchestrator:
    """Camada operacional — não altera QuantumTrend Pro Core."""

    def __init__(self) -> None:
        self._last_regime: str | None = None

    def startup_recovery(self, reconciler: PositionReconciler, *, symbol: str, strategy: str):
        transition(PlatformState.SYNCING, "iniciando recovery", force=True)
        position, meta = run_position_recovery(reconciler, symbol=symbol, strategy=strategy)
        locked, reason = is_risk_locked()
        if locked:
            alert_recovery_required(reason or "inconsistência")
            transition(PlatformState.RISK_LOCKED, reason or "recovery", force=True)
        else:
            transition(PlatformState.ANALYZING, "recovery concluído", force=True)
        return position, meta

    def assess_tick_data(self, engine: Any, ind_df: Any) -> dict[str, Any]:
        tf = engine.config.exchange.timeframe
        report = assess_dataframe(ind_df, timeframe=tf, source="engine")
        if not report.ok:
            alert_data_quality(report.score, report.issues)
        return report.to_dict()

    def gate_operations(self, engine: Any, *, data_ok: bool) -> tuple[bool, str | None]:
        locked, reason = is_risk_locked()
        if locked:
            return False, reason or "RISK_LOCKED — confirme em Configurações ou /api/platform/ack-risk"
        if not can_execute_event("trade"):
            return False, f"estado {load_platform_state().get('state')} não permite operações"
        if not data_ok:
            return False, "data quality abaixo do mínimo — redownload recomendado"
        paused_scaling = (load_platform_state().get("capital_scaling") or {}).get("paused")
        if paused_scaling:
            return False, "health combinado < 40 — operações pausadas"
        return True, None

    def check_entry_filters(self, engine: Any, ind_df: Any, idx: int) -> tuple[bool, str | None]:
        row = ind_df.iloc[idx]
        exhaustion = detect_trend_exhaustion(row, candle_close=float(row.get("close", 0)))
        patch_platform_state(trend_exhaustion=exhaustion.to_dict())
        if exhaustion.exhausted:
            return False, f"trend exhaustion: {exhaustion.reason}"
        return True, None

    def post_signal(
        self,
        engine: Any,
        *,
        signal: Any,
        ctx: Any,
        outcome: dict,
        candle: Any,
    ) -> None:
        action = outcome.get("action")
        executed = action in {"entry", "exit"}
        decision_type = "exit" if signal.action == SignalAction.EXIT_LONG else "entry" if signal.action == SignalAction.ENTER_LONG else "hold"

        if ctx is not None:
            regime = getattr(ctx, "regime", None)
            regime_val = regime.value if regime else None
            if regime_val and regime_val != self._last_regime:
                label = (getattr(ctx, "meta", None) or {}).get("regime_label", regime_val)
                alert_regime_change(str(label))
                self._last_regime = regime_val

            score = float(getattr(ctx, "alignment_score", 0) or 0)
            if score >= 90:
                alert_high_score(score)

            breakdown = getattr(ctx, "alignment_breakdown", None) or {}
            if breakdown:
                explanation = build_score_explanation(
                    total=score,
                    breakdown=breakdown,
                    threshold=int((getattr(signal, "metadata", None) or {}).get("alignment_threshold") or 80),
                )
                persist_score_explanation(explanation, strategy=engine.config.strategy.name)

        if decision_type in {"entry", "exit", "hold"} and (
            executed
            or outcome.get("block_reason")
            or signal.action in (SignalAction.ENTER_LONG, SignalAction.EXIT_LONG)
            or outcome.get("action") in {"paused", "skipped_no_balance", "blocked", "entry_failed"}
        ):
            record_decision(
                journal=engine.journal,
                symbol=engine.config.exchange.symbol,
                strategy=engine.config.strategy.name,
                decision_type=decision_type if signal.action != SignalAction.HOLD else "ignored",
                signal=signal,
                ctx=ctx,
                executed=executed,
                block_reason=outcome.get("block_reason"),
                action=action,
            )

        if executed and action == "entry":
            alert_trade_open(engine.config.exchange.symbol, float(candle.close))

    def post_tick(self, engine: Any, outcome: dict) -> None:
        collect_engine_metrics()
        sync_state_from_runtime()

        from atlas.services.quantum_service import get_quantum_status

        q = get_quantum_status()
        engine_h = (load_platform_state().get("engine_health") or {}).get("score", 100)
        data_h = (load_platform_state().get("data_quality") or {}).get("score", 100)
        strat_h = float(q.get("health_score") or 0)
        if strat_h and strat_h < 50:
            alert_health_drop(strat_h)
        apply_capital_scaling(strategy_health=strat_h or 70, engine_health=float(engine_h), data_health=float(data_h))

    def on_error(self, engine: Any, error: str) -> None:
        alert_sync_failure(error)
        transition(PlatformState.ERROR, error, force=True)


platform_orchestrator = PlatformOrchestrator()
