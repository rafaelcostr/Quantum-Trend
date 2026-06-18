from __future__ import annotations


def confidence_level(
    *,
    total_trades: int,
    profit_factor: float,
    sharpe: float | None,
    max_drawdown_pct: float,
    years_tested: float | None,
) -> tuple[str, str, float]:
    score = 50.0

    if total_trades >= 80:
        score += 20
    elif total_trades >= 50:
        score += 15
    elif total_trades >= 30:
        score += 8
    else:
        score -= 15

    if years_tested is not None:
        if years_tested >= 3:
            score += 10
        elif years_tested >= 2:
            score += 5
        else:
            score -= 5

    if profit_factor >= 1.5:
        score += 10
    elif profit_factor >= 1.2:
        score += 5
    elif profit_factor < 1.0:
        score -= 10

    if sharpe is not None:
        if sharpe >= 1.0:
            score += 10
        elif sharpe >= 0.7:
            score += 5
        elif sharpe < 0.5:
            score -= 10

    if max_drawdown_pct <= 0.15:
        score += 10
    elif max_drawdown_pct <= 0.25:
        score += 5
    elif max_drawdown_pct > 0.30:
        score -= 15

    score = max(0, min(100, score))

    if score >= 70:
        return "Alta Confiança", "🟢", score
    if score >= 45:
        return "Média Confiança", "🟡", score
    return "Baixa Confiança", "🔴", score
