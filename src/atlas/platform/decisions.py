"""Decision Engine — narrativas auditáveis de cada decisão operacional."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from atlas.core.models import SignalAction
from atlas.platform.models import DecisionRecord
from atlas.platform.score_explanation import build_score_explanation
from atlas.platform.store import append_decision, patch_platform_state


def _tf_label(aligned: bool) -> str:
    return "alinhado" if aligned else "desalinhado"


def build_decision_narrative(
    *,
    decision_type: str,
    signal_action: str,
    reason: str,
    ctx: Any | None,
    alignment_score: float | None = None,
    threshold: int | None = None,
    block_reason: str | None = None,
    executed: bool = False,
) -> str:
    lines: list[str] = []

    if decision_type == "entry" and executed:
        lines.append("Entrada executada.")
        lines.append("Entrou comprado.")
    elif decision_type == "entry" and not executed:
        lines.append("Entrada ignorada.")
    elif decision_type == "exit" and executed:
        lines.append("Saída executada.")
    elif decision_type == "exit":
        lines.append("Saída não executada.")
    else:
        lines.append("Operação ignorada.")

    if ctx is not None:
        regime = getattr(ctx, "regime", None)
        regime_label = (getattr(ctx, "meta", None) or {}).get("regime_label") or (regime.value if regime else "—")
        lines.append("")
        lines.append(f"Regime:\n{regime_label}")
        lines.append("")
        lines.append(f"1D:\n{_tf_label(getattr(ctx, 'macro_bull', False))}")
        lines.append("")
        lines.append(f"4H:\n{_tf_label(getattr(ctx, 'confirm_bull', False))}")
        module = (getattr(ctx, "meta", None) or {}).get("entry_module") or reason.split()[0] if reason else "—"
        if decision_type == "entry":
            lines.append("")
            lines.append(f"Módulo:\n{module}")

    if alignment_score is not None:
        lines.append("")
        lines.append(f"Alignment Score:\n{alignment_score:.0f}")
    if threshold is not None and not executed:
        lines.append("")
        lines.append(f"Mínimo:\n{threshold}")

    lines.append("")
    lines.append(f"Motivo:\n{block_reason or reason}")
    return "\n".join(lines)


def record_decision(
    *,
    journal: Any,
    symbol: str,
    strategy: str,
    decision_type: str,
    signal: Any,
    ctx: Any | None = None,
    executed: bool = False,
    block_reason: str | None = None,
    action: str | None = None,
) -> DecisionRecord:
    alignment_score = None
    threshold = None
    breakdown = {}
    if ctx is not None:
        alignment_score = getattr(ctx, "alignment_score", None)
        breakdown = getattr(ctx, "alignment_breakdown", None) or {}
        threshold = (getattr(signal, "metadata", None) or {}).get("alignment_threshold")
    if threshold is None and breakdown:
        threshold = 80

    narrative = build_decision_narrative(
        decision_type=decision_type,
        signal_action=getattr(signal, "action", SignalAction.HOLD).value if signal else "HOLD",
        reason=getattr(signal, "reason", "") if signal else "",
        ctx=ctx,
        alignment_score=float(alignment_score) if alignment_score is not None else None,
        threshold=int(threshold) if threshold is not None else None,
        block_reason=block_reason,
        executed=executed,
    )

    outcome = action or ("executed" if executed else "ignored")
    meta: dict[str, Any] = {
        "signal": getattr(signal, "action", SignalAction.HOLD).value if signal else None,
        "reason": getattr(signal, "reason", "") if signal else "",
        "executed": executed,
        "block_reason": block_reason,
    }
    if breakdown:
        meta["score_explanation"] = build_score_explanation(
            total=float(alignment_score or 0),
            breakdown=breakdown,
            threshold=int(threshold or 80),
        )

    record = DecisionRecord(
        decision_type=decision_type,
        outcome=outcome,
        narrative=narrative,
        ts=datetime.now(timezone.utc).isoformat(),
        symbol=symbol,
        strategy=strategy,
        meta=meta,
    )
    append_decision(record.to_dict())
    patch_platform_state(last_decision=record.to_dict())
    journal.log("decision", symbol, **record.to_dict())
    return record
