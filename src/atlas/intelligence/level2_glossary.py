from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from atlas.intelligence.glossary import metric_reading
from atlas.intelligence.models import EducationalMetric, MetricReading

StatusFn = Callable[[float | None], tuple[str, str, str]]


@dataclass(frozen=True)
class MetricGuide:
    key: str
    label: str
    what_is: str
    why_matters: str
    bands: str
    status_fn: StatusFn
    fmt: Callable[[float], str]


def status_sortino(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v >= 2.0:
        return "excellent", "🟢", "Excelente"
    if v >= 1.2:
        return "good", "🟢", "Muito Bom"
    if v >= 0.8:
        return "acceptable", "🟡", "Aceitável"
    if v >= 0.4:
        return "poor", "🟠", "Fraco"
    return "poor", "🔴", "Ruim"


def status_recovery(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v >= 5:
        return "excellent", "🟢", "Excelente"
    if v >= 3:
        return "good", "🟢", "Bom"
    if v >= 1:
        return "acceptable", "🟡", "Aceitável"
    return "poor", "🔴", "Ruim"


def status_payoff(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v >= 3:
        return "excellent", "🟢", "Excelente"
    if v >= 2:
        return "good", "🟢", "Muito Bom"
    if v >= 1.2:
        return "acceptable", "🟡", "Aceitável"
    if v >= 1.0:
        return "poor", "🟠", "Fraco"
    return "poor", "🔴", "Ruim"


def status_calmar(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v >= 2.0:
        return "excellent", "🟢", "Excelente"
    if v >= 1.0:
        return "good", "🟢", "Muito Bom"
    if v >= 0.5:
        return "acceptable", "🟡", "Aceitável"
    return "poor", "🔴", "Fraco"


def status_exposure(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if 0.25 <= v <= 0.65:
        return "good", "🟢", "Moderada"
    if v < 0.25:
        return "acceptable", "🟡", "Baixa"
    if v <= 0.85:
        return "acceptable", "🟡", "Alta"
    return "poor", "🟠", "Muito Alta"


def status_streak_win(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v >= 5:
        return "excellent", "🟢", "Forte"
    if v >= 3:
        return "good", "🟢", "Boa"
    return "acceptable", "🟡", "Normal"


def status_streak_loss(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v <= 3:
        return "excellent", "🟢", "Controlada"
    if v <= 5:
        return "acceptable", "🟡", "Moderada"
    if v <= 8:
        return "poor", "🟠", "Alta"
    return "poor", "🔴", "Crítica"


LEVEL2_GUIDES: list[MetricGuide] = [
    MetricGuide(
        "sortino_ratio",
        "Sortino Ratio",
        "Versão do Sharpe que penaliza apenas a volatilidade negativa (downside).",
        "Mede retorno ajustado ao risco de perdas, mais relevante que Sharpe para estratégias assimétricas.",
        "≥2 Excelente · ≥1.2 Muito Bom · ≥0.8 Aceitável · <0.4 Fraco",
        status_sortino,
        lambda v: f"{v:.2f}",
    ),
    MetricGuide(
        "recovery_factor",
        "Recovery Factor",
        "Lucro líquido dividido pelo maior drawdown em valor absoluto.",
        "Indica capacidade de recuperar perdas. Abaixo de 1, a estratégia não recuperou o pior buraco.",
        "<1 Ruim · 1–3 Aceitável · 3–5 Bom · >5 Excelente",
        status_recovery,
        lambda v: f"{v:.2f}",
    ),
    MetricGuide(
        "payoff_ratio",
        "Payoff Ratio",
        "Ganho médio por trade vencedor dividido pela perda média.",
        "Estratégias com win rate baixo precisam de payoff alto para serem viáveis.",
        "<1 Ruim · 1–2 Aceitável · 2–3 Muito Bom · >3 Excelente",
        status_payoff,
        lambda v: f"{v:.2f}",
    ),
    MetricGuide(
        "calmar_ratio",
        "Calmar Ratio",
        "CAGR dividido pelo drawdown máximo.",
        "Resume retorno anualizado por unidade de risco extremo — métrica institucional comum.",
        "<0.5 Fraco · 0.5–1 Aceitável · 1–2 Muito Bom · >2 Excelente",
        status_calmar,
        lambda v: f"{v:.2f}",
    ),
    MetricGuide(
        "market_exposure",
        "Exposição ao Mercado",
        "Percentual do tempo total em que a estratégia manteve posição aberta.",
        "Exposição muito alta aumenta risco de mercado; muito baixa pode indicar oportunidades perdidas.",
        "<25% Baixa · 25–65% Moderada · >85% Muito Alta",
        status_exposure,
        lambda v: f"{v:.1%}",
    ),
    MetricGuide(
        "max_win_streak",
        "Maior Sequência de Ganhos",
        "Máximo de trades vencedores consecutivos.",
        "Sequências longas de ganhos podem mascarar dependência de poucos períodos favoráveis.",
        "3+ Boa · 5+ Forte",
        status_streak_win,
        lambda v: f"{int(v)}",
    ),
    MetricGuide(
        "max_loss_streak",
        "Maior Sequência de Perdas",
        "Máximo de trades perdedores consecutivos.",
        "Impacta gestão emocional e risco de abandono da estratégia no pior momento.",
        "≤3 Controlada · 4–5 Moderada · 6–8 Alta · >8 Crítica",
        status_streak_loss,
        lambda v: f"{int(v)}",
    ),
]


def build_educational_metrics(values: dict) -> list[EducationalMetric]:
    items: list[EducationalMetric] = []
    for guide in LEVEL2_GUIDES:
        raw = values.get(guide.key)
        if raw is None and guide.key not in values:
            continue
        val = float(raw) if raw is not None else None
        display = guide.fmt(val) if val is not None else "N/A"
        reading = metric_reading(guide.key, guide.label, val, display, guide.status_fn)
        how = f"Seu valor: **{display}** → {reading.emoji} {reading.status_text}"
        items.append(
            EducationalMetric(
                reading=reading,
                what_is=guide.what_is,
                why_matters=guide.why_matters,
                how_interpret=how,
                bands_text=guide.bands,
            )
        )
    return items
