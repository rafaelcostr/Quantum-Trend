"""ATLAS Intelligence — dashboard UI (Níveis 1, 2 e 3)."""
from __future__ import annotations

import streamlit as st

from atlas.intelligence.models import StrategyAnalysis
from atlas.intelligence.report import render_ai_report


def _render_level1_tab(analysis: StrategyAnalysis) -> None:
    l1 = analysis.level1
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Atlas Score", f"{l1.atlas_score:.0f}", f"{l1.score_emoji} {l1.score_label}")
    with c2:
        st.metric("Confiança", l1.confidence, l1.confidence_emoji)
    with c3:
        st.metric("Overfitting", l1.overfitting_risk, l1.overfitting_emoji)

    st.info(l1.summary)

    cols = st.columns(4)
    display_keys = ["profit_factor", "drawdown", "expectancy", "sharpe", "return", "trades"]
    metrics_map = {m.key: m for m in l1.metrics}
    for i, key in enumerate(display_keys):
        m = metrics_map.get(key)
        if not m:
            continue
        with cols[i % 4]:
            st.markdown(
                f"""
                <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin-bottom:8px;">
                  <div style="color:#8b949e;font-size:12px;">{m.label}</div>
                  <div style="font-size:22px;font-weight:600;">{m.display}</div>
                  <div style="font-size:13px;">{m.emoji} {m.status_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.subheader("Pontos Fortes")
        for s in l1.strengths:
            st.write(s)
    with col_b:
        st.subheader("Pontos Fracos")
        for w in l1.weaknesses:
            st.write(w)
    with col_c:
        st.subheader("Riscos")
        for r in l1.risks:
            st.write(r)

    st.subheader("Checklist BACKTEST → PAPER")
    passed = sum(1 for c in l1.promotion_backtest_paper if c["ok"])
    total = len(l1.promotion_backtest_paper)
    st.progress(passed / total if total else 0, text=f"{passed}/{total} critérios")
    for chk in l1.promotion_backtest_paper:
        icon = "✅" if chk["ok"] else "❌"
        st.write(f"{icon} **{chk['label']}** — `{chk['value']}`")


def _render_level2_tab(analysis: StrategyAnalysis) -> None:
    l2 = analysis.level2
    if l2 is None:
        st.warning("Diagnóstico indisponível.")
        return

    st.markdown("### Diagnóstico automático")
    st.success(l2.diagnosis)

    for edu in l2.metrics:
        r = edu.reading
        with st.expander(f"{r.emoji} **{r.label}** — {r.display} ({r.status_text})", expanded=False):
            st.markdown(f"**O que é:** {edu.what_is}")
            st.markdown(f"**Por que importa:** {edu.why_matters}")
            st.markdown(f"**Faixas:** {edu.bands_text}")
            st.markdown(edu.how_interpret)


def _render_level3_tab(analysis: StrategyAnalysis) -> None:
    l3 = analysis.level3
    if l3 is None:
        st.warning("Research Lab indisponível.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Overfitting (L3)", l3.overfitting_risk, l3.overfitting_emoji)
    with c2:
        wf = "✅ Sim" if l3.has_walkforward else "⏳ Pendente"
        st.metric("Walk-forward", wf)

    if not l3.has_walkforward:
        st.info(
            "Execute walk-forward para métricas OOS:\n\n"
            "`atlas research walkforward --config config/backtest_mm200_v2.yaml`"
        )

    st.markdown("### Research Interpreter")
    st.success(l3.diagnosis)

    mc_cols = st.columns(3)
    vals = l3.values
    with mc_cols[0]:
        v = vals.get("mc_return_median")
        st.metric("MC Retorno Mediano", f"{v:.1%}" if v is not None else "N/A")
    with mc_cols[1]:
        v = vals.get("mc_return_worst")
        st.metric("MC Pior Retorno (P5)", f"{v:.1%}" if v is not None else "N/A")
    with mc_cols[2]:
        v = vals.get("mc_dd_worst")
        st.metric("MC Pior DD (P95)", f"{v:.1%}" if v is not None else "N/A")

    for edu in l3.metrics:
        r = edu.reading
        with st.expander(f"{r.emoji} **{r.label}** — {r.display} ({r.status_text})", expanded=False):
            st.markdown(f"**O que é:** {edu.what_is}")
            st.markdown(f"**Por que importa:** {edu.why_matters}")
            st.markdown(f"**Faixas:** {edu.bands_text}")
            st.markdown(edu.how_interpret)


def render_intelligence(analysis: StrategyAnalysis) -> None:
    st.markdown("## ATLAS Intelligence")
    st.caption(
        f"**{analysis.strategy}** · {analysis.market} {analysis.timeframe} · "
        f"{analysis.period_start or '?'} → {analysis.period_end or '?'}"
    )

    tab1, tab2, tab3 = st.tabs(["Nível 1 — Decisão Rápida", "Nível 2 — Diagnóstico", "Nível 3 — Research"])

    with tab1:
        _render_level1_tab(analysis)
    with tab2:
        _render_level2_tab(analysis)
    with tab3:
        _render_level3_tab(analysis)

    st.divider()
    report_md = render_ai_report(analysis)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "📋 Baixar Relatório (.md)",
            data=report_md,
            file_name=f"atlas_{analysis.strategy}_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with c2:
        if st.button("📋 COPIAR RELATÓRIO PARA IA", use_container_width=True):
            st.code(report_md, language="markdown")
            st.success("Selecione o texto acima e copie (Ctrl+C).")


# retrocompat
def render_level1(analysis: StrategyAnalysis) -> None:
    render_intelligence(analysis)
