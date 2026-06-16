"""ATLAS Intelligence — dashboard UI (Níveis 1, 2 e 3)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from atlas.dashboard.actions import run_compare, run_export_all_reports
from atlas.dashboard.download_ui import download_bytes_button, save_report_markdown, show_export_result
from atlas.dashboard.theme import cyber_metric_card, cyber_page_header, cyber_section_title
from atlas.intelligence.analyzer import analyze_path
from atlas.intelligence.models import StrategyAnalysis
from atlas.intelligence.report import render_ai_report
from atlas.strategies.metadata import report_select_options


def _pct(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val:.2%}"


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
                cyber_metric_card(m.label, m.display, m.status_text, m.emoji),
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
        st.info("Execute walk-forward na secao **Pesquisa** para metricas OOS.")

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


def _render_metadata_panel(analysis: StrategyAnalysis) -> None:
    meta = analysis.metadata
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("**Strategy**")
        st.write(meta.get("strategy") or analysis.strategy)
        st.caption(f"v{meta.get('strategy_version', 'N/A')}")
    with c2:
        st.markdown("**Strategy Type**")
        st.write(meta.get("strategy_type") or "N/A")
        st.caption(meta.get("mode", analysis.source))
    with c3:
        st.markdown("**Market / TF**")
        tf = str(meta.get("timeframe") or analysis.timeframe).upper()
        st.write(f"{meta.get('market', analysis.market)} · {tf}")
        st.caption(f"{analysis.period_start or '?'} → {analysis.period_end or '?'}")
    with c4:
        st.markdown("**Risco / Custos**")
        st.write(meta.get("risk_model") or "N/A")
        st.caption(
            f"Size: {meta.get('position_size', 'N/A')} · "
            f"Fee {_pct(meta.get('fee_rate'))} · Slip {_pct(meta.get('slippage_rate'))}"
        )
    if meta.get("config_file"):
        st.caption(f"Config: `{meta['config_file']}`")
    if meta.get("legacy_report"):
        st.warning(
            "Relatorio antigo (sem metadados completos). "
            "Va em **Pesquisa → Rodar TODAS** para gerar relatorios com estrategia e config identificados."
        )


def _render_ranking(project_root: Path) -> None:
    with st.expander("Exportar todos os backtests", expanded=True):
        st.caption(
            "1 relatorio unico com todas as estrategias para IA + ZIP + individuais separados."
        )
        if st.button("EXPORTAR TODOS (.zip)", type="primary", key="intel_btn_export_all", use_container_width=True):
            with st.spinner("Gerando relatorios..."):
                st.session_state["export_result"] = run_export_all_reports(project_root)
            st.rerun()

        export = st.session_state.get("export_result")
        if export:
            show_export_result(project_root, export, key_prefix="intel_export")
        else:
            st.info("Clique em **EXPORTAR TODOS** para gerar os arquivos.")

        if st.button("Atualizar ranking", key="intel_btn_ranking", use_container_width=True):
            with st.spinner("Analisando..."):
                st.session_state["intel_compare_rows"] = run_compare(project_root)
            st.rerun()

        res = st.session_state.get("intel_compare_rows")
        if res and res.get("ok"):
            df = pd.DataFrame(res["rows"])
            if "Retorno" in df.columns:
                df["Retorno"] = df["Retorno"].apply(lambda x: f"{x:.1%}" if x is not None else "N/A")
            if "DD" in df.columns:
                df["DD"] = df["DD"].apply(lambda x: f"{x:.1%}" if x is not None else "N/A")
            st.dataframe(df, use_container_width=True, hide_index=True)


def render_intelligence_page(project_root: Path) -> None:
    """Pagina completa: escolher relatorio, ranking e analise."""
    reports_dir = project_root / "data" / "reports"
    options = report_select_options(reports_dir)

    st.markdown(
        cyber_page_header("ATLAS INTELLIGENCE", "Analise individual ou comparativo de todos os backtests"),
        unsafe_allow_html=True,
    )

    if not options:
        st.warning("Nenhum relatorio em `data/reports/`.")
        st.info(
            "1. Va em **Pesquisa**\n"
            "2. Baixe dados **4h** e/ou **1d**\n"
            "3. Clique **Rodar TODAS as estrategias**\n"
            "4. Volte aqui e escolha o relatorio"
        )
        return

    labels = [label for label, _ in options]
    default_idx = 0
    if "intel_report_label" in st.session_state and st.session_state["intel_report_label"] in labels:
        default_idx = labels.index(st.session_state["intel_report_label"])

    selected_label = st.selectbox(
        "Relatorio de backtest",
        labels,
        index=default_idx,
        key="intel_report_label",
        help="Cada linha = um backtest salvo (estrategia + timeframe + tipo).",
    )
    sel_path = next(path for label, path in options if label == selected_label)

    _render_ranking(project_root)

    analysis = analyze_path(sel_path)
    _render_metadata_panel(analysis)
    st.divider()
    render_intelligence(analysis, project_root=project_root, download_key=f"dl_report_{sel_path.stem}")


def render_intelligence(
    analysis: StrategyAnalysis,
    *,
    project_root: Path | None = None,
    download_key: str = "dl_single_report",
) -> None:
    meta = analysis.metadata
    stype = meta.get("strategy_type", "")
    version = meta.get("strategy_version", "")
    tf = str(meta.get("timeframe") or analysis.timeframe).upper()
    header = f"**{analysis.strategy}**"
    if version:
        header += f" v{version}"
    if stype:
        header += f" · {stype}"
    st.markdown("### Analise")
    st.caption(
        f"{header} · {meta.get('market', analysis.market)} {tf} · "
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
    if project_root is not None:
        saved = save_report_markdown(project_root, analysis, report_md)
        st.caption(f"Individual salvo: `{saved.relative_to(project_root)}`")
    c1, c2 = st.columns(2)
    with c1:
        download_bytes_button(
            "Baixar este relatorio (.md)",
            report_md.encode("utf-8"),
            f"atlas_{analysis.strategy}_report.md",
            mime="text/markdown",
            key=download_key,
        )
    with c2:
        if st.button("COPIAR RELATORIO PARA IA", key=f"copy_{download_key}", use_container_width=True):
            st.code(report_md, language="markdown")
            st.success("Selecione o texto acima e copie (Ctrl+C).")


# retrocompat
def render_level1(analysis: StrategyAnalysis) -> None:
    render_intelligence(analysis)
