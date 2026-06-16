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

## NÍVEL 3 — Research
_Pendente (Sprint 3 — walk-forward, Monte Carlo, OOS)_

---

## Checklist BACKTEST → PAPER
{chr(10).join(promo_lines)}

---

## Recommendation
{l1.summary}
"""
