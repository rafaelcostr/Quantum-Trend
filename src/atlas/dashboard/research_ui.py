"""Dashboard — Pesquisa (download, backtest, compare, walk-forward)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from atlas.dashboard.actions import (
    list_config_files,
    run_backtest,
    run_compare,
    run_download,
    run_walkforward,
)


def render_research(project_root: Path) -> None:
    st.markdown("## Pesquisa")
    st.caption("Backtest e analise de estrategias — tudo pelo dashboard, sem terminal.")

    configs = list_config_files(project_root)
    if not configs:
        st.error("Nenhum config/backtest*.yaml encontrado.")
        return

    config_labels = [c.name for c in configs]
    default_idx = next((i for i, c in enumerate(configs) if c.name == "backtest_mm200_v2.yaml"), 0)

    tab_dl, tab_bt, tab_cmp, tab_wf = st.tabs(
        ["Baixar dados", "Backtest", "Comparar", "Walk-forward"]
    )

    with tab_dl:
        st.markdown("### Baixar candles historicos")
        cfg_dl = st.selectbox("Config de dados", config_labels, index=default_idx, key="dl_cfg")
        force = st.checkbox("Forcar re-download", key="dl_force")
        to_db = st.checkbox("Salvar no PostgreSQL", key="dl_db")
        if st.button("Baixar dados", type="primary", key="btn_dl"):
            with st.spinner("Baixando via CCXT..."):
                res = run_download(project_root, f"config/{cfg_dl}", force=force, to_db=to_db)
            if res.get("ok"):
                st.success(f"{res['candles']} candles — {res['symbol']} {res['timeframe']}")
                if res.get("db_rows"):
                    st.info(f"PostgreSQL: ate {res['db_rows']} linhas")
            else:
                st.error(res.get("error", "Falha"))

    with tab_bt:
        st.markdown("### Rodar backtest")
        cfg_bt = st.selectbox("Config backtest", config_labels, index=default_idx, key="bt_cfg")
        if st.button("Executar backtest", type="primary", key="btn_bt"):
            with st.spinner("Rodando backtest event-driven..."):
                res = run_backtest(project_root, f"config/{cfg_bt}")
            if res.get("ok"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Retorno", f"{res['net_profit_pct']:.1%}")
                c2.metric("Profit Factor", f"{res['profit_factor']:.2f}")
                c3.metric("Max DD", f"{res['max_drawdown_pct']:.1%}")
                c4.metric("Trades", res["total_trades"])
                st.caption(
                    f"Buy & Hold: {res['buy_hold_pct']:.1%} · "
                    f"Win rate: {res['win_rate']:.1%} · "
                    f"Sharpe: {res.get('sharpe_ratio') or 'N/A'}"
                )
                st.success(f"Relatorio salvo: `{res['report_path']}`")
                st.info("Va em **ATLAS Intelligence** para analise completa.")
            else:
                st.error(res.get("error", "Falha"))

    with tab_cmp:
        st.markdown("### Ranking Atlas Score")
        if st.button("Atualizar ranking", type="primary", key="btn_cmp"):
            with st.spinner("Analisando relatorios..."):
                res = run_compare(project_root)
            st.session_state["compare_rows"] = res

        res = st.session_state.get("compare_rows")
        if not res:
            st.info("Clique em **Atualizar ranking** (rode backtests antes).")
        elif not res.get("ok"):
            st.warning(res.get("error"))
        else:
            df = pd.DataFrame(res["rows"])
            if "Retorno" in df.columns:
                df["Retorno"] = df["Retorno"].apply(lambda x: f"{x:.1%}" if x is not None else "N/A")
            if "DD" in df.columns:
                df["DD"] = df["DD"].apply(lambda x: f"{x:.1%}" if x is not None else "N/A")
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_wf:
        st.markdown("### Walk-forward (IS/OOS)")
        cfg_wf = st.selectbox("Config", config_labels, index=default_idx, key="wf_cfg")
        train_pct = st.slider("In-sample %", 0.50, 0.90, 0.70, 0.05, key="wf_pct")
        if st.button("Executar walk-forward", type="primary", key="btn_wf"):
            with st.spinner("Split 70/30 + backtests..."):
                res = run_walkforward(project_root, f"config/{cfg_wf}", train_pct=train_pct)
            st.session_state["wf_result"] = res

        res = st.session_state.get("wf_result")
        if res and res.get("ok"):
            c1, c2, c3 = st.columns(3)
            c1.metric("IS retorno", f"{res['is_return']:.1%}")
            c2.metric("OOS retorno", f"{res['oos_return']:.1%}")
            wfe = res.get("wfe")
            c3.metric("WFE", f"{wfe:.0%}" if wfe is not None else "N/A")
            st.caption(
                f"Split: {res['split_timestamp']} · "
                f"OOS PF: {res['oos_pf']:.2f} · "
                f"Trades IS/OOS: {res['is_trades']}/{res['oos_trades']}"
            )
            st.success(f"Salvo: `{res['path']}`")
