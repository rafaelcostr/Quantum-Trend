from __future__ import annotations

from atlas.intelligence.models import StrategyAnalysis


def _l2_line(analysis: StrategyAnalysis, key: str) -> str:
    if not analysis.level2:
        return "N/A"
    for edu in analysis.level2.metrics:
        if edu.reading.key == key:
            r = edu.reading
            return f"{r.emoji} {r.display} ({r.status_text})"
    return "N/A"


def _l3_line(analysis: StrategyAnalysis, key: str) -> str:
    if not analysis.level3:
        return "N/A"
    for edu in analysis.level3.metrics:
        if edu.reading.key == key:
            r = edu.reading
            return f"{r.emoji} {r.display} ({r.status_text})"
    return "N/A"


def render_ai_report(analysis: StrategyAnalysis) -> str:
    l1 = analysis.level1
    raw = analysis.raw

    def m(key: str) -> str:
        for item in l1.metrics:
            if item.key == key:
                return f"{item.emoji} {item.display} ({item.status_text})"
        return "N/A"

    promo_lines = []
    for chk in l1.promotion_backtest_paper:
        mark = "✓" if chk["ok"] else "✗"
        promo_lines.append(f"- [{mark}] {chk['label']} — {chk['value']}")

    strengths = "\n".join(f"- {s}" for s in l1.strengths)
    weaknesses = "\n".join(f"- {w}" for w in l1.weaknesses)
    risks = "\n".join(f"- {r}" for r in l1.risks)

    cagr = raw.get("cagr")
    cagr_txt = f"{cagr:.1%}" if cagr is not None else "N/A"

    l2_diag = analysis.level2.diagnosis if analysis.level2 else "_Indisponível_"
    l3 = analysis.level3
    l3_diag = l3.diagnosis if l3 else "_Indisponível_"
    l3_of = f"{l3.overfitting_emoji} {l3.overfitting_risk}" if l3 else "N/A"

    boot_low = analysis.raw.get("bootstrap_ci_low")
    boot_high = analysis.raw.get("bootstrap_ci_high")
    boot_txt = "N/A"
    if boot_low is not None and boot_high is not None:
        boot_txt = f"${boot_low:.2f} — ${boot_high:.2f} (95%)"

    return f"""# ATLAS QUANT REPORT

**Strategy:** {analysis.strategy}
**Market:** {analysis.market}
**Timeframe:** {analysis.timeframe}
**Period:** {analysis.period_start or '?'} → {analysis.period_end or '?'}
**Source:** {analysis.source}

---

## ATLAS SCORE: {l1.atlas_score:.0f}/100 — {l1.score_emoji} {l1.score_label}
**Confidence:** {l1.confidence_emoji} {l1.confidence}
**Overfitting Risk (L1):** {l1.overfitting_emoji} {l1.overfitting_risk}

---

## NÍVEL 1 — Decisão Rápida

| Métrica | Valor |
|---------|-------|
| Retorno Total | {m('return')} |
| CAGR | {cagr_txt} |
| Drawdown Máx. | {m('drawdown')} |
| Profit Factor | {m('profit_factor')} |
| Expectância | {m('expectancy')} |
| Sharpe | {m('sharpe')} |
| Trades | {m('trades')} |

**Resumo:** {l1.summary}

### Pontos Fortes
{strengths}

### Pontos Fracos
{weaknesses}

### Riscos
{risks}

---

## NÍVEL 2 — Diagnóstico

**Diagnóstico automático:** {l2_diag}

| Métrica | Valor |
|---------|-------|
| Sortino | {_l2_line(analysis, 'sortino_ratio')} |
| Recovery Factor | {_l2_line(analysis, 'recovery_factor')} |
| Payoff Ratio | {_l2_line(analysis, 'payoff_ratio')} |
| Calmar Ratio | {_l2_line(analysis, 'calmar_ratio')} |
| Exposição Mercado | {_l2_line(analysis, 'market_exposure')} |
| Seq. Ganhos | {_l2_line(analysis, 'max_win_streak')} |
| Seq. Perdas | {_l2_line(analysis, 'max_loss_streak')} |

---

## NÍVEL 3 — Research Lab

**Research Interpreter:** {l3_diag}

**Overfitting (IS vs OOS):** {l3_of}

| Métrica | Valor |
|---------|-------|
| Retorno OOS | {_l3_line(analysis, 'oos_return')} |
| Profit Factor OOS | {_l3_line(analysis, 'oos_profit_factor')} |
| Walk-Forward Efficiency | {_l3_line(analysis, 'walk_forward_efficiency')} |
| Monte Carlo P5 Retorno | {_l3_line(analysis, 'mc_return_worst')} |
| Monte Carlo P95 DD | {_l3_line(analysis, 'mc_dd_worst')} |
| Kelly Criterion | {_l3_line(analysis, 'kelly_fraction')} |
| Ulcer Index | {_l3_line(analysis, 'ulcer_index')} |
| Skewness | {_l3_line(analysis, 'skewness')} |
| Kurtosis | {_l3_line(analysis, 'kurtosis')} |

**Bootstrap PnL médio (95% CI):** {boot_txt}

---

## Checklist BACKTEST → PAPER
{chr(10).join(promo_lines)}

---

## Recommendation
{l1.summary}
"""
