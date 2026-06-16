from __future__ import annotations

from typing import Any


def build_level2_narrative(values: dict[str, Any], level1_raw: dict[str, Any]) -> str:
    parts: list[str] = []

    rf = values.get("recovery_factor")
    payoff = values.get("payoff_ratio")
    exposure = values.get("market_exposure")
    loss_streak = values.get("max_loss_streak", 0)
    sortino = values.get("sortino_ratio")
    calmar = values.get("calmar_ratio")
    win_rate = level1_raw.get("win_rate", 0)

    if rf is not None and rf >= 3:
        parts.append("A estratégia demonstra boa capacidade de recuperação de drawdowns (Recovery Factor elevado).")
    elif rf is not None and rf < 1:
        parts.append("O Recovery Factor abaixo de 1 indica que o lucro não compensou o maior buraco de equity.")

    if exposure is not None:
        if exposure < 0.25:
            parts.append("A exposição ao mercado é baixa — a estratégia passa grande parte do tempo fora do mercado.")
        elif exposure <= 0.65:
            parts.append("A exposição ao mercado é moderada, equilibrando participação e tempo em caixa.")
        else:
            parts.append("A exposição ao mercado é alta — o capital fica investido na maior parte do período.")

    if payoff is not None and payoff >= 1.5:
        parts.append("O Payoff Ratio é saudável, compensando um win rate possivelmente baixo.")
    elif payoff is not None and payoff < 1.0:
        parts.append("O Payoff Ratio abaixo de 1 sugere que perdas médias superam ganhos médios.")

    if loss_streak >= 6:
        parts.append(
            f"A sequência máxima de {loss_streak} perdas consecutivas exige disciplina emocional e sizing conservador."
        )
    elif loss_streak >= 4:
        parts.append(
            f"Sequências de até {loss_streak} perdas são esperáveis — mantenha o plano de risco definido."
        )

    if sortino is not None and sortino >= 1.0:
        parts.append("O Sortino indica retorno favorável em relação ao risco de quedas.")
    elif sortino is not None and sortino < 0.5:
        parts.append("O Sortino baixo sugere retorno insuficiente para o risco de perdas observado.")

    if calmar is not None and calmar >= 1.0:
        parts.append("O Calmar Ratio mostra retorno anualizado competitivo para o drawdown sofrido.")

    if win_rate < 0.20 and (payoff or 0) >= 2:
        parts.append(
            "Padrão típico de trend following: poucos acertos, mas ganhos maiores que perdas quando acerta."
        )

    if not parts:
        parts.append("Métricas de diagnóstico dentro de faixas neutras — aprofunde no Nível 3 (Research) se necessário.")

    return " ".join(parts)
