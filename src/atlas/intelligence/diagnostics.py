from __future__ import annotations

from typing import Any


def overfitting_risk_l1(
    *,
    total_trades: int,
    profit_factor: float,
    max_drawdown_pct: float,
    net_profit_pct: float,
    buy_hold_pct: float | None = None,
) -> tuple[str, str]:
    risk_score = 0

    if total_trades < 30:
        risk_score += 2
    elif total_trades < 50:
        risk_score += 1

    if profit_factor > 2.5:
        risk_score += 2
    elif profit_factor > 2.0:
        risk_score += 1

    if max_drawdown_pct > 0.30 and net_profit_pct > 0.5:
        risk_score += 2
    elif max_drawdown_pct > 0.25:
        risk_score += 1

    if buy_hold_pct is not None and net_profit_pct > buy_hold_pct * 1.5 and total_trades < 60:
        risk_score += 1

    if risk_score >= 4:
        return "Alto Risco", "🔴"
    if risk_score >= 2:
        return "Médio Risco", "🟡"
    return "Baixo Risco", "🟢"


def build_diagnostics(
    values: dict[str, Any],
    *,
    buy_hold_pct: float | None = None,
) -> tuple[list[str], list[str], list[str], str]:
    strengths: list[str] = []
    weaknesses: list[str] = []
    risks: list[str] = []

    pf = values["profit_factor"]
    dd = values["max_drawdown_pct"]
    trades = int(values["total_trades"])
    sharpe = values.get("sharpe_ratio")
    ret = values["net_profit_pct"]
    exp = values["expectancy_pct"]
    win_rate = values.get("win_rate", 0)

    if pf >= 1.3:
        strengths.append("✓ Profit Factor saudável")
    if dd <= 0.20:
        strengths.append("✓ Drawdown controlado")
    if trades >= 50:
        strengths.append("✓ Boa quantidade de trades para validação")
    if sharpe is not None and sharpe >= 1.0:
        strengths.append("✓ Sharpe ratio sólido")
    if exp > 0:
        strengths.append("✓ Expectância positiva por trade")

    if sharpe is not None and sharpe < 0.7:
        weaknesses.append("⚠ Sharpe moderado ou baixo")
    if buy_hold_pct is not None and ret < buy_hold_pct:
        weaknesses.append("⚠ Retorno abaixo do buy & hold no mesmo período")
    if win_rate < 0.25 and pf < 1.5:
        weaknesses.append("⚠ Win rate baixo com payoff dependente de poucos ganhos")
    if trades < 50:
        weaknesses.append("⚠ Amostra de trades ainda limitada")
    if dd > 0.25:
        weaknesses.append("⚠ Drawdown acima do limite ideal para promoção")

    of_label, _ = overfitting_risk_l1(
        total_trades=trades,
        profit_factor=pf,
        max_drawdown_pct=dd,
        net_profit_pct=ret,
        buy_hold_pct=buy_hold_pct,
    )
    if of_label == "Alto Risco":
        risks.append("⚠ Possível overfitting — validar com walk-forward")
    elif of_label == "Médio Risco":
        risks.append("⚠ Risco moderado de overfitting — ampliar testes")

    if dd > 0.30:
        risks.append("⚠ Drawdown elevado — risco psicológico e de capital")
    if ret > 0.5 and trades < 60:
        risks.append("⚠ Possível dependência de mercado bull")
    if pf > 2.0 and trades < 40:
        risks.append("⚠ Profit Factor alto com poucos trades — cautela")

    if not strengths:
        strengths.append("— Nenhum ponto forte destacado no momento")
    if not weaknesses:
        weaknesses.append("— Sem fraquezas críticas detectadas")
    if not risks:
        risks.append("— Sem riscos elevados detectados no Nível 1")

    parts = []
    if pf >= 1.3 and dd <= 0.25:
        parts.append("A estratégia combina fator de lucro aceitável com risco moderado.")
    elif ret < 0:
        parts.append("A estratégia apresentou retorno negativo no período analisado.")
    else:
        parts.append("A estratégia mostra sinais mistos entre retorno e risco.")

    if trades >= 50:
        parts.append("O número de trades é suficiente para análise preliminar.")
    else:
        parts.append("O número de trades ainda é limitado para conclusões definitivas.")

    if dd > 0.25:
        parts.append("Recomenda-se cautela antes de promover para paper.")
    elif pf >= 1.2 and trades >= 50:
        parts.append("Pode ser candidata a paper trading após revisar o checklist.")

    summary = " ".join(parts)
    return strengths, weaknesses, risks, summary


def promotion_checklist_backtest_paper(
    values: dict[str, Any],
    *,
    level3_values: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    from atlas.quantum.gates import merge_promotion_checklists, promotion_checklist_backtest, promotion_checklist_paper

    backtest_checks = promotion_checklist_backtest(values)
    paper_checks = promotion_checklist_paper(values)

    l3 = level3_values or {}
    oos_ret = l3.get("oos_return")
    oos_pf = l3.get("oos_profit_factor")
    if oos_ret is not None:
        wf_ok = oos_ret > 0 and (oos_pf is None or oos_pf >= 1.0)
        wf_value = f"OOS {oos_ret:.1%}"
        if oos_pf is not None:
            wf_value += f", PF {oos_pf:.2f}"
    else:
        wf_ok = False
        wf_value = "Pendente — rode walk-forward"

    walkforward = [
        {"label": "Walk-forward OOS positivo", "ok": wf_ok, "value": wf_value, "stage": "research"},
    ]
    sharpe = values.get("sharpe_ratio")
    if sharpe is not None:
        walkforward.append(
            {
                "label": "Sharpe >= 1.0 (referência)",
                "ok": sharpe >= 1.0,
                "value": f"{sharpe:.2f}",
                "stage": "research",
            }
        )
    return merge_promotion_checklists(backtest_checks, paper_checks, walkforward)
