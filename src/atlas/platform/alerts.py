"""Alert System — informativos, atenção e críticos."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from atlas.core.log import log_event
from atlas.platform.models import AlertSeverity
from atlas.platform.store import append_alert, load_platform_state


def emit_alert(
    *,
    severity: AlertSeverity,
    category: str,
    message: str,
    meta: dict[str, Any] | None = None,
    telegram: bool = True,
) -> dict[str, Any]:
    record = {
        "severity": severity.value,
        "category": category,
        "message": message,
        "ts": datetime.now(timezone.utc).isoformat(),
        "meta": meta or {},
    }
    append_alert(record)

    if telegram and severity == AlertSeverity.CRITICAL:
        try:
            from atlas.monitoring.alerts import get_alerts

            alerts = get_alerts()
            if alerts.configured:
                alerts.send(f"🚨 <b>CRÍTICO</b> [{category}]\n{message}")
        except Exception as exc:
            log_event(
                30,
                "platform.alert.telegram.failed",
                module="platform.alerts",
                category=category,
                error=str(exc)[:240],
            )
    return record


def list_alerts(*, limit: int = 50, severity: str | None = None) -> list[dict[str, Any]]:
    alerts = list(load_platform_state().get("alerts") or [])
    if severity:
        alerts = [a for a in alerts if a.get("severity") == severity]
    return alerts[:limit]


def alert_center_payload() -> dict[str, Any]:
    alerts = list_alerts(limit=100)
    grouped = {
        "info": [a for a in alerts if a.get("severity") == AlertSeverity.INFO.value],
        "warning": [a for a in alerts if a.get("severity") == AlertSeverity.WARNING.value],
        "critical": [a for a in alerts if a.get("severity") == AlertSeverity.CRITICAL.value],
    }
    return {
        "total": len(alerts),
        "unread_critical": len(grouped["critical"]),
        "groups": grouped,
        "recent": alerts[:20],
    }


# Helpers por categoria (Parte 5)
def alert_regime_change(label: str) -> None:
    emit_alert(severity=AlertSeverity.INFO, category="regime", message=f"Novo regime detectado: {label}")


def alert_high_score(score: float) -> None:
    emit_alert(severity=AlertSeverity.INFO, category="alignment", message=f"Alignment Score acima de 90: {score:.0f}")


def alert_trade_open(symbol: str, price: float) -> None:
    emit_alert(severity=AlertSeverity.INFO, category="trade", message=f"Nova operação aberta em {symbol} @ {price:.2f}")


def alert_health_drop(score: float) -> None:
    emit_alert(severity=AlertSeverity.WARNING, category="health", message=f"Health Score caiu para {score:.0f}")


def alert_data_quality(score: float, issues: list[str]) -> None:
    emit_alert(
        severity=AlertSeverity.WARNING if score >= 40 else AlertSeverity.CRITICAL,
        category="data_quality",
        message=f"Dados inconsistentes — score {score:.0f}",
        meta={"issues": issues[:5]},
    )


def alert_kill_switch() -> None:
    emit_alert(severity=AlertSeverity.CRITICAL, category="kill_switch", message="Kill Switch acionado — operações bloqueadas")


def alert_recovery_required(reason: str) -> None:
    emit_alert(severity=AlertSeverity.CRITICAL, category="recovery", message=f"Recovery necessário: {reason}")


def alert_sync_failure(detail: str) -> None:
    emit_alert(severity=AlertSeverity.CRITICAL, category="sync", message=f"Falha de sincronização: {detail}")
