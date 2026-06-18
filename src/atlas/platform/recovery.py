"""Position Recovery Engine — reconstrói estado após falhas ou reinício."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from atlas.core.models import Position
from atlas.platform.models import RecoveryReport
from atlas.platform.store import patch_platform_state, set_risk_locked
from atlas.runtime.reconciler import PositionReconciler


def _fetch_open_orders(broker: Any, symbol: str) -> list[dict[str, Any]]:
    fn = getattr(broker, "fetch_open_orders", None)
    if not callable(fn):
        return []
    try:
        return fn(symbol)
    except Exception as exc:
        return [{"error": str(exc)}]


def _check_stop_targets(position: Position | None, open_orders: list[dict]) -> list[str]:
    issues: list[str] = []
    if position is None:
        return issues
    has_stop = position.stop_price is not None
    has_target = position.target_price is not None
    order_types = {str(o.get("type", "")).lower() for o in open_orders if isinstance(o, dict)}
    if has_stop and not any("stop" in t for t in order_types):
        issues.append("stop interno definido mas sem ordem stop na exchange")
    if has_target and not any("limit" in t or "take" in t for t in order_types):
        issues.append("take profit interno sem ordem correspondente na exchange")
    return issues


def run_position_recovery(
    reconciler: PositionReconciler,
    *,
    symbol: str,
    strategy: str,
) -> tuple[Position | None, dict[str, Any]]:
    """Sincroniza posição interna com exchange, ordens e journal."""
    position, meta = reconciler.reconcile_on_startup()
    open_orders = _fetch_open_orders(reconciler.broker, symbol)
    issues: list[str] = []

    warning = meta.get("warning")
    if warning:
        issues.append(str(warning))
    if meta.get("broker_error"):
        issues.append(f"broker: {meta['broker_error']}")

    for err_order in open_orders:
        if isinstance(err_order, dict) and err_order.get("error"):
            issues.append(f"ordens abertas: {err_order['error']}")

    issues.extend(_check_stop_targets(position, [o for o in open_orders if isinstance(o, dict) and not o.get("error")]))

    source = str(meta.get("source") or "unknown")
    critical_sources = {"journal_mismatch", "exchange_orphan"}
    risk_locked = bool(issues) and (source in critical_sources or meta.get("broker_error"))

    report = RecoveryReport(
        ok=not risk_locked,
        position_source=source,
        issues=issues,
        open_orders=[o for o in open_orders if isinstance(o, dict)],
        risk_locked=risk_locked,
        reconciled_at=datetime.now(timezone.utc).isoformat(),
        meta={**meta, "strategy": strategy, "symbol": symbol},
    )

    patch_platform_state(recovery=report.to_dict())

    if risk_locked:
        set_risk_locked(True, "; ".join(issues[:3]) or "inconsistência na sincronização")

    return position, {**meta, "recovery": report.to_dict(), "open_orders": open_orders, "issues": issues}
