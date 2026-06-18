from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PlatformState(str, Enum):
    STOPPED = "STOPPED"
    SYNCING = "SYNCING"
    ANALYZING = "ANALYZING"
    BACKTESTING = "BACKTESTING"
    PAPER = "PAPER"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    LIVE = "LIVE"
    COOLDOWN = "COOLDOWN"
    RISK_LOCKED = "RISK_LOCKED"
    ERROR = "ERROR"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRecord:
    severity: AlertSeverity
    category: str
    message: str
    ts: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "ts": self.ts,
            "meta": self.meta,
        }


@dataclass
class DecisionRecord:
    decision_type: str
    outcome: str
    narrative: str
    ts: str
    symbol: str
    strategy: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_type": self.decision_type,
            "outcome": self.outcome,
            "narrative": self.narrative,
            "ts": self.ts,
            "symbol": self.symbol,
            "strategy": self.strategy,
            "meta": self.meta,
        }


@dataclass
class RecoveryReport:
    ok: bool
    position_source: str
    issues: list[str]
    open_orders: list[dict[str, Any]]
    risk_locked: bool
    reconciled_at: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "position_source": self.position_source,
            "issues": self.issues,
            "open_orders": self.open_orders,
            "risk_locked": self.risk_locked,
            "reconciled_at": self.reconciled_at,
            "meta": self.meta,
        }


@dataclass
class DataQualityReport:
    score: float
    issues: list[str]
    candle_count: int
    last_candle_ts: str | None
    ok: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "issues": self.issues,
            "candle_count": self.candle_count,
            "last_candle_ts": self.last_candle_ts,
            "ok": self.ok,
        }


@dataclass
class StressTestReport:
    scenario: str
    survived: bool
    summary: str
    metrics: dict[str, Any]
    ts: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "survived": self.survived,
            "summary": self.summary,
            "metrics": self.metrics,
            "ts": self.ts,
        }
