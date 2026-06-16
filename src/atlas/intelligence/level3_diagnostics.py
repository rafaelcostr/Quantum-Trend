from __future__ import annotations

from typing import Any


def overfitting_risk_l3(values: dict[str, Any]) -> tuple[str, str]:
    if values.get("oos_return") is None:
        return "Sem dados OOS", "⚪"

    score = 0
    is_ret = values.get("is_return")
    oos_ret = values.get("oos_return")
    wfe = values.get("walk_forward_efficiency")
    oos_pf = values.get("oos_profit_factor")
    mc_worst = values.get("mc_return_worst")

    if is_ret is not None and is_ret > 0 and oos_ret is not None:
        ratio = oos_ret / is_ret
        if ratio < 0.2:
            score += 3
        elif ratio < 0.5:
            score += 2
        elif ratio < 0.7:
            score += 1

    if oos_ret is not None and oos_ret < 0:
        score += 2
    if oos_pf is not None and oos_pf < 1.0:
        score += 2
    elif oos_pf is not None and oos_pf < 1.2:
        score += 1

    if wfe is not None:
        if wfe < 0.25:
            score += 2
        elif wfe < 0.50:
            score += 1

    if mc_worst is not None and mc_worst < -0.25:
        score += 1

    if score >= 5:
        return "Alto — provável overfitting", "🔴"
    if score >= 3:
        return "Médio — validar com mais dados", "🟡"
    return "Baixo — generalização aceitável", "🟢"


def build_level3_narrative(values: dict[str, Any]) -> str:
    parts: list[str] = []

    if values.get("oos_return") is None:
        return (
            "Walk-forward ainda não executado. Rode `atlas research walkforward --config <yaml>` "
            "para gerar métricas OOS e atualizar este diagnóstico."
        )

    oos_ret = values.get("oos_return")
    is_ret = values.get("is_return")
    wfe = values.get("walk_forward_efficiency")
    oos_pf = values.get("oos_profit_factor")
    mc_worst = values.get("mc_return_worst")
    mc_dd = values.get("mc_dd_worst")
    kelly = values.get("kelly_fraction")

    if oos_ret is not None and oos_ret > 0:
        parts.append(f"O período out-of-sample registrou retorno positivo ({oos_ret:.1%}).")
    elif oos_ret is not None:
        parts.append(f"O retorno out-of-sample foi negativo ({oos_ret:.1%}) — sinal de alerta para promoção.")

    if is_ret is not None and oos_ret is not None and is_ret > 0:
        deg = 1 - (oos_ret / is_ret)
        if deg > 0.5:
            parts.append(
                "Há degradação severa entre in-sample e out-of-sample — possível ajuste excessivo aos dados."
            )
        elif deg > 0.25:
            parts.append("A performance caiu moderadamente fora da amostra — comportamento esperado em parte.")
        else:
            parts.append("A estratégia manteve boa parte do desempenho fora da amostra.")

    if wfe is not None:
        if wfe >= 0.6:
            parts.append(f"Walk-Forward Efficiency de {wfe:.0%} indica boa robustez.")
        elif wfe >= 0.3:
            parts.append(f"WFE de {wfe:.0%} é frágil — parte do edge pode ser específico do período IS.")
        else:
            parts.append(f"WFE de {wfe:.0%} é muito baixo — investigar overfitting antes de paper.")

    if oos_pf is not None:
        if oos_pf >= 1.3:
            parts.append("O Profit Factor OOS confirma edge fora da amostra.")
        elif oos_pf < 1.0:
            parts.append("Profit Factor OOS abaixo de 1 — a estratégia perde dinheiro no período de validação.")

    if mc_worst is not None:
        if mc_worst >= 0:
            parts.append("Monte Carlo: mesmo no pior cenário (P5), o retorno permanece não-negativo.")
        else:
            parts.append(
                f"Monte Carlo: no pior 5% das permutações, o retorno cai para {mc_worst:.1%} — prepare capital de reserva."
            )

    if mc_dd is not None and mc_dd > 0.35:
        parts.append(
            f"O drawdown máximo simulado (P95) atinge {mc_dd:.1%} — sizing conservador é essencial."
        )

    if kelly is not None and kelly > 0:
        frac = min(kelly / 4, 0.25)
        parts.append(
            f"Kelly teórico sugere até {kelly:.1%} por trade; na prática use fração Kelly (~{frac:.1%})."
        )

    of_label, _ = overfitting_risk_l3(values)
    if "Alto" in of_label:
        parts.append("Conclusão: risco elevado de overfitting — não promover sem mais validação.")
    elif "Baixo" in of_label:
        parts.append("Conclusão: sinais de generalização aceitáveis para considerar paper com cautela.")

    return " ".join(parts)
