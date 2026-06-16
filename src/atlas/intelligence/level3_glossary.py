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


def status_oos_return(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v >= 0.30:
        return "excellent", "🟢", "Forte"
    if v >= 0.10:
        return "good", "🟢", "Bom"
    if v >= 0:
        return "acceptable", "🟡", "Positivo"
    return "poor", "🔴", "Negativo"


def status_oos_pf(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v >= 1.5:
        return "excellent", "🟢", "Forte"
    if v >= 1.0:
        return "acceptable", "🟡", "OK"
    return "poor", "🔴", "Ruim"


def status_wfe(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v >= 0.75:
        return "excellent", "🟢", "Robusto"
    if v >= 0.50:
        return "good", "🟢", "Aceitável"
    if v >= 0.30:
        return "acceptable", "🟡", "Frágil"
    return "poor", "🔴", "Suspeito"


def status_mc_worst(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v >= 0:
        return "excellent", "🟢", "Resiliente"
    if v >= -0.15:
        return "acceptable", "🟡", "Moderado"
    if v >= -0.30:
        return "poor", "🟠", "Arriscado"
    return "poor", "🔴", "Crítico"


def status_mc_dd(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v <= 0.20:
        return "excellent", "🟢", "Controlado"
    if v <= 0.30:
        return "acceptable", "🟡", "Moderado"
    if v <= 0.45:
        return "poor", "🟠", "Alto"
    return "poor", "🔴", "Extremo"


def status_kelly(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if 0.05 <= v <= 0.25:
        return "good", "🟢", "Conservador"
    if v < 0.05:
        return "acceptable", "🟡", "Muito Baixo"
    if v <= 0.40:
        return "acceptable", "🟡", "Agressivo"
    return "poor", "🔴", "Perigoso"


def status_ulcer(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v <= 5:
        return "excellent", "🟢", "Suave"
    if v <= 12:
        return "good", "🟢", "Moderado"
    if v <= 20:
        return "acceptable", "🟡", "Elevado"
    return "poor", "🔴", "Doloroso"


def status_skew(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v >= 0.5:
        return "good", "🟢", "Assimétrico +"
    if v >= -0.5:
        return "acceptable", "🟡", "Neutro"
    return "poor", "🟠", "Cauda Esq."


def status_kurtosis(v: float | None) -> tuple[str, str, str]:
    if v is None:
        return "na", "⚪", "N/A"
    if v <= 3:
        return "good", "🟢", "Normal"
    if v <= 6:
        return "acceptable", "🟡", "Caudas Pesadas"
    return "poor", "🔴", "Extremo"


LEVEL3_GUIDES: list[MetricGuide] = [
    MetricGuide(
        "oos_return",
        "Retorno Out-of-Sample",
        "Retorno no período de teste (30% final) não usado no treino walk-forward.",
        "Valida se a estratégia generaliza fora da amostra in-sample.",
        ">30% Forte · 10–30% Bom · >0% Positivo · <0% Negativo",
        status_oos_return,
        lambda v: f"{v:.1%}",
    ),
    MetricGuide(
        "oos_profit_factor",
        "Profit Factor OOS",
        "Fator de lucro calculado apenas nos trades out-of-sample.",
        "PF OOS < 1 indica que a estratégia perde dinheiro no período de validação.",
        ">1.5 Forte · 1.0–1.5 Aceitável · <1 Ruim",
        status_oos_pf,
        lambda v: f"{v:.2f}",
    ),
    MetricGuide(
        "walk_forward_efficiency",
        "Walk-Forward Efficiency",
        "Razão entre retorno OOS e retorno IS (eficiência de generalização).",
        "WFE baixo sugere que o desempenho in-sample não se repete fora da amostra.",
        "≥0.75 Robusto · 0.5–0.75 Aceitável · <0.3 Suspeito",
        status_wfe,
        lambda v: f"{v:.0%}",
    ),
    MetricGuide(
        "mc_return_worst",
        "Monte Carlo — Pior Retorno (P5)",
        "Percentil 5 dos retornos em 1000 simulações bootstrap dos trades.",
        "Estima o pior cenário plausível reordenando os trades aleatoriamente.",
        "≥0% Resiliente · -15% Moderado · <-30% Crítico",
        status_mc_worst,
        lambda v: f"{v:.1%}",
    ),
    MetricGuide(
        "mc_dd_worst",
        "Monte Carlo — Pior DD (P95)",
        "Percentil 95 do drawdown máximo nas simulações Monte Carlo.",
        "Mostra quanto de drawdown extra pode ocorrer por azar na sequência de trades.",
        "≤20% Controlado · 20–30% Moderado · >45% Extremo",
        status_mc_dd,
        lambda v: f"{v:.1%}",
    ),
    MetricGuide(
        "kelly_fraction",
        "Kelly Criterion",
        "Fração ótima teórica de capital por trade (win rate e payoff).",
        "Kelly cheio é agressivo — traders usam fração Kelly (¼–½) na prática.",
        "5–25% Conservador · >40% Perigoso",
        status_kelly,
        lambda v: f"{v:.1%}",
    ),
    MetricGuide(
        "ulcer_index",
        "Ulcer Index",
        "Raiz da média dos quadrados dos drawdowns percentuais da equity.",
        "Mede a 'dor' psicológica dos buracos — menor é melhor que volatilidade bruta.",
        "≤5 Suave · 5–12 Moderado · >20 Doloroso",
        status_ulcer,
        lambda v: f"{v:.1f}",
    ),
    MetricGuide(
        "skewness",
        "Skewness (Assimetria)",
        "Mede se os retornos dos trades têm cauda positiva ou negativa.",
        "Trend following costuma ter skew positivo (poucos grandes ganhos).",
        "≥0.5 Assimétrico + · -0.5 a 0.5 Neutro · <-0.5 Cauda Esquerda",
        status_skew,
        lambda v: f"{v:.2f}",
    ),
    MetricGuide(
        "kurtosis",
        "Kurtosis (Caudas)",
        "Mede a 'peso' das caudas da distribuição de retornos dos trades.",
        "Kurtosis alta indica eventos extremos mais frequentes que uma normal.",
        "≤3 Normal · 3–6 Caudas Pesadas · >6 Extremo",
        status_kurtosis,
        lambda v: f"{v:.2f}",
    ),
]


def build_level3_educational_metrics(values: dict) -> list[EducationalMetric]:
    items: list[EducationalMetric] = []
    for guide in LEVEL3_GUIDES:
        raw = values.get(guide.key)
        if raw is None:
            continue
        val = float(raw)
        display = guide.fmt(val)
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
