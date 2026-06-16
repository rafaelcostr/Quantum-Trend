from __future__ import annotations

from typing import Callable

from atlas.intelligence.models import MetricReading

StatusFn = Callable[[float | None], tuple[str, str, str]]  # status, emoji, text


def _band(
    value: float | None,
    rules: list[tuple[float, str, str, str]],
    *,
    higher_is_better: bool = True,
    na_label: str = "N/A",
) -> tuple[str, str, str]:
    if value is None:
        return "na", "⚪", na_label
    ordered = rules if higher_is_better else list(reversed(rules))
    for threshold, status, emoji, text in ordered:
        if higher_is_better and value >= threshold:
            return status, emoji, text
        if not higher_is_better and value <= threshold:
            return status, emoji, text
    return rules[-1][1], rules[-1][2], rules[-1][3]


def status_profit_factor(pf: float | None) -> tuple[str, str, str]:
    return _band(
        pf,
        [
            (2.0, "excellent", "🟢", "Excelente"),
            (1.5, "good", "🟢", "Muito Bom"),
            (1.3, "acceptable", "🟡", "Aceitável"),
            (1.0, "poor", "🟠", "Fraco"),
            (-1, "poor", "🔴", "Ruim"),
        ],
    )


def status_drawdown(dd: float | None) -> tuple[str, str, str]:
    if dd is None:
        return "na", "⚪", "N/A"
    if dd <= 0.10:
        return "excellent", "🟢", "Excelente"
    if dd <= 0.20:
        return "good", "🟢", "Muito Bom"
    if dd <= 0.30:
        return "acceptable", "🟡", "Aceitável"
    if dd <= 0.40:
        return "poor", "🟠", "Alto"
    return "poor", "🔴", "Crítico"


def status_sharpe(sharpe: float | None) -> tuple[str, str, str]:
    return _band(
        sharpe,
        [
            (2.0, "excellent", "🟢", "Excelente"),
            (1.5, "good", "🟢", "Muito Bom"),
            (1.0, "acceptable", "🟡", "Aceitável"),
            (0.5, "poor", "🟠", "Fraco"),
            (-99, "poor", "🔴", "Ruim"),
        ],
    )


def status_expectancy(exp_pct: float | None) -> tuple[str, str, str]:
    return _band(
        exp_pct,
        [
            (0.02, "excellent", "🟢", "Excelente"),
            (0.01, "good", "🟢", "Muito Bom"),
            (0.005, "acceptable", "🟡", "Aceitável"),
            (0.0, "poor", "🟠", "Fraco"),
            (-99, "poor", "🔴", "Negativa"),
        ],
    )


def status_return(ret: float | None) -> tuple[str, str, str]:
    return _band(
        ret,
        [
            (1.0, "excellent", "🟢", "Excelente"),
            (0.5, "good", "🟢", "Muito Bom"),
            (0.2, "acceptable", "🟡", "Aceitável"),
            (0.0, "poor", "🟠", "Fraco"),
            (-99, "poor", "🔴", "Negativo"),
        ],
    )


def status_trades(n: int | None) -> tuple[str, str, str]:
    if n is None:
        return "na", "⚪", "N/A"
    if n >= 100:
        return "excellent", "🟢", "Excelente"
    if n >= 50:
        return "good", "🟢", "Muito Bom"
    if n >= 30:
        return "acceptable", "🟡", "Aceitável"
    if n >= 15:
        return "poor", "🟠", "Insuficiente"
    return "poor", "🔴", "Muito Poucos"


def metric_reading(
    key: str,
    label: str,
    value: float | int | None,
    display: str,
    status_fn: StatusFn,
) -> MetricReading:
    status, emoji, text = status_fn(float(value) if value is not None else None)
    return MetricReading(
        key=key,
        label=label,
        value=value,
        display=display,
        status=status,
        emoji=emoji,
        status_text=text,
    )
