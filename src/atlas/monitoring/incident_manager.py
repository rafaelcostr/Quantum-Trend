from __future__ import annotations

import hashlib
import json
import smtplib
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from atlas.core.env import get_settings, project_root
from atlas.core.log import log_event

_PATH = project_root() / "data" / "runtime" / "incidents.json"
_MAX_INCIDENTS = 500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _incident_id(key: str) -> str:
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _load() -> list[dict[str, Any]]:
    if not _PATH.is_file():
        return []
    try:
        raw = json.loads(_PATH.read_text(encoding="utf-8"))
        return list(raw if isinstance(raw, list) else raw.get("items", []))
    except (json.JSONDecodeError, OSError, TypeError):
        return []


def _save(items: list[dict[str, Any]]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(items[:_MAX_INCIDENTS], indent=2, default=str), encoding="utf-8")


def _post_json(url: str, payload: dict[str, Any]) -> bool:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, OSError) as exc:
        log_event(30, "monitoring.channel.webhook.failed", module="monitoring.incidents", error=str(exc)[:240])
        return False


def configured_channels() -> dict[str, bool]:
    settings = get_settings()
    return {
        "telegram": bool(settings.telegram_bot_token and settings.telegram_chat_id),
        "discord": bool(settings.discord_webhook_url),
        "email": bool(settings.smtp_host and settings.alert_email_to),
        "webhook": bool(settings.alert_webhook_url),
    }


def _send_email(subject: str, body: str) -> bool:
    settings = get_settings()
    if not settings.smtp_host or not settings.alert_email_to:
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.alert_email_from or settings.smtp_username or "quantum-trend@localhost"
    msg["To"] = settings.alert_email_to
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except OSError as exc:
        log_event(30, "monitoring.channel.email.failed", module="monitoring.incidents", error=str(exc)[:240])
        return False


def notify_channels(incident: dict[str, Any], *, resolved: bool = False) -> dict[str, bool]:
    settings = get_settings()
    title = "Incidente resolvido" if resolved else "Incidente aberto"
    body = (
        f"{title}: {incident.get('type')}\n"
        f"Módulo: {incident.get('module') or '-'}\n"
        f"Estratégia: {incident.get('strategy') or '-'}\n"
        f"Mensagem: {incident.get('message')}\n"
        f"Status: {incident.get('status')}\n"
        f"Horário: {incident.get('updated_at')}"
    )
    results: dict[str, bool] = {}
    if settings.telegram_bot_token and settings.telegram_chat_id:
        try:
            from atlas.monitoring.alerts import get_alerts

            icon = "✅" if resolved else "🚨"
            results["telegram"] = get_alerts().send(f"{icon} <b>{title}</b>\n<pre>{body}</pre>")
        except Exception as exc:
            log_event(30, "monitoring.channel.telegram.failed", module="monitoring.incidents", error=str(exc)[:240])
            results["telegram"] = False
    if settings.discord_webhook_url:
        results["discord"] = _post_json(settings.discord_webhook_url, {"content": f"```{body}```"})
    if settings.alert_webhook_url:
        results["webhook"] = _post_json(settings.alert_webhook_url, {"event": "incident_resolved" if resolved else "incident_opened", "incident": incident})
    if settings.smtp_host and settings.alert_email_to:
        results["email"] = _send_email(f"Quantum-Trend: {title}", body)
    return results


def open_incident(
    *,
    type: str,
    message: str,
    module: str,
    severity: str = "warning",
    strategy: str | None = None,
    metadata: dict[str, Any] | None = None,
    key: str | None = None,
    notify: bool = True,
) -> dict[str, Any]:
    items = _load()
    incident_key = key or f"{type}:{module}:{strategy or '-'}"
    inc_id = _incident_id(incident_key)
    now = _now()
    for item in items:
        if item.get("id") == inc_id and item.get("status") == "open":
            item["message"] = message
            item["severity"] = severity
            item["metadata"] = metadata or {}
            item["updated_at"] = now
            item["count"] = int(item.get("count", 1)) + 1
            _save(items)
            return item
    incident = {
        "id": inc_id,
        "key": incident_key,
        "type": type,
        "message": message,
        "severity": severity,
        "module": module,
        "strategy": strategy,
        "metadata": metadata or {},
        "status": "open",
        "opened_at": now,
        "updated_at": now,
        "resolved_at": None,
        "count": 1,
    }
    items.insert(0, incident)
    _save(items)
    if notify:
        incident["channels"] = notify_channels(incident)
        _save(items)
    return incident


def resolve_incident(key_or_id: str, *, message: str | None = None, notify: bool = True) -> dict[str, Any] | None:
    items = _load()
    now = _now()
    target_id = _incident_id(key_or_id)
    for item in items:
        if item.get("id") in {key_or_id, target_id} or item.get("key") == key_or_id:
            if item.get("status") != "resolved":
                item["status"] = "resolved"
                item["resolved_at"] = now
                item["updated_at"] = now
                if message:
                    item["resolution"] = message
                if notify:
                    item["resolve_channels"] = notify_channels(item, resolved=True)
            _save(items)
            return item
    return None


def list_incidents(*, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    items = _load()
    if status:
        items = [i for i in items if i.get("status") == status]
    return items[:limit]


def incidents_payload() -> dict[str, Any]:
    items = list_incidents(limit=200)
    open_items = [i for i in items if i.get("status") == "open"]
    return {
        "total": len(items),
        "open": len(open_items),
        "resolved": len([i for i in items if i.get("status") == "resolved"]),
        "channels": configured_channels(),
        "items": items[:100],
        "open_items": open_items[:50],
    }
