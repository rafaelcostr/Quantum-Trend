from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricReading:
    key: str
    label: str
    value: float | int | str | None
    display: str
    status: str  # excellent | good | acceptable | poor | na
    emoji: str  # 🟢 🟡 🟠 🔴
    status_text: str  # Excelente, Aceitável, etc.


@dataclass
class Level1Snapshot:
    atlas_score: float
    score_label: str
    score_emoji: str
    confidence: str
    confidence_emoji: str
    overfitting_risk: str
    overfitting_emoji: str
    metrics: list[MetricReading]
    strengths: list[str]
    weaknesses: list[str]
    risks: list[str]
    summary: str
    promotion_backtest_paper: list[dict[str, Any]]


@dataclass
class EducationalMetric:
    reading: MetricReading
    what_is: str
    why_matters: str
    how_interpret: str
    bands_text: str


@dataclass
class Level2Snapshot:
    metrics: list[EducationalMetric]
    diagnosis: str
    values: dict[str, Any] = field(default_factory=dict)


@dataclass
class Level3Snapshot:
    metrics: list[EducationalMetric]
    diagnosis: str
    overfitting_risk: str
    overfitting_emoji: str
    values: dict[str, Any] = field(default_factory=dict)
    has_walkforward: bool = False


@dataclass
class StrategyAnalysis:
    strategy: str
    source: str
    market: str
    timeframe: str
    period_start: str | None
    period_end: str | None
    level1: Level1Snapshot
    level2: Level2Snapshot | None = None
    level3: Level3Snapshot | None = None
    raw: dict[str, Any] = field(default_factory=dict)
