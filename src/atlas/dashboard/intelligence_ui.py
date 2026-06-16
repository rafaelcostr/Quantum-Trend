"""ATLAS Intelligence — Level 1 UI components for Streamlit."""
from __future__ import annotations

import streamlit as st

from atlas.intelligence.models import StrategyAnalysis
from atlas.intelligence.report import render_ai_report


def render_level1(analysis: StrategyAnalysis) -> None:
    l1 = analysis.level1

    st.markdown("## ATLAS Intelligence — Nível 1")
    st.caption(
        f"**{analysis.strategy}** · {analysis.market} {analysis.timeframe} · "
        f"{analysis.period_start or '?'} → {analysis.period_end or '?'}"
    )

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

    st.divider()
    report_md = render_ai_report(analysis)
    st.download_button(
        "📋 Baixar Relatório (.md)",
        data=report_md,
        file_name=f"atlas_{analysis.strategy}_report.md",
        mime="text/markdown",
    )
    if st.button("📋 COPIAR RELATÓRIO PARA IA", use_container_width=True):
        st.code(report_md, language="markdown")
        st.success("Relatório exibido acima — selecione e copie (Ctrl+C).")

    with st.expander("Nível 2 — Diagnóstico (em breve)"):
        st.write("Sprint 2: Sortino, Recovery Factor, Payoff, Calmar, exposição, sequências.")
    with st.expander("Nível 3 — Research Lab (em breve)"):
        st.write("Sprint 3: Walk-forward, Monte Carlo, OOS, Kelly, Ulcer Index.")
