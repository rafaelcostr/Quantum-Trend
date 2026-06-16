"""Dashboard — Pesquisa (download, backtest, compare, walk-forward)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from atlas.dashboard.actions import (
    list_config_files,
    run_backtest_dashboard,
    run_compare,
    run_download,
    run_export_all_reports,
    run_walkforward,
)
from atlas.dashboard.download_ui import show_export_result
from atlas.dashboard.strategy_config import QUOTE_ASSETS

QUOTE_MODE_OPTIONS = ("both", "USDT", "USDC")  # legado — preferir research_both_quotes


def _init_research_state() -> None:
    if "research_both_quotes" not in st.session_state:
        st.session_state["research_both_quotes"] = True
    if "research_quote_single" not in st.session_state:
        st.session_state["research_quote_single"] = "USDT"


def _research_opts() -> tuple[list[str], list[str]]:
    tf_mode = st.session_state.get("research_tf_mode", "4h")
    tfs = ["4h", "1d"] if tf_mode == "both" else [tf_mode]
    if st.session_state.get("research_both_quotes", True):
        quotes = list(QUOTE_ASSETS)
    else:
        quotes = [st.session_state.get("research_quote_single", "USDT")]
    return tfs, quotes


def _run_batch_backtest(
    project_root: Path,
    configs: list[Path],
    *,
    timeframes: list[str] | None = None,
    quotes: list[str] | None = None,
) -> None:
    tfs, qs = _research_opts()
    if timeframes:
        tfs = timeframes
    if quotes:
        qs = quotes
    total_steps = len(configs) * len(tfs) * len(qs)
    progress = st.progress(0, text="Iniciando...")
    rows_acc: list[dict] = []
    errors_acc: list[str] = []
    step = 0
    for q in qs:
        for tf in tfs:
            for cfg_path in configs:
                step += 1
                progress.progress(
                    step / max(total_steps, 1),
                    text=f"{cfg_path.name} · {tf} · BTC/{q}",
                )
                res = run_backtest_dashboard(
                    project_root,
                    f"config/{cfg_path.name}",
                    timeframe=tf,
                    quote=q,
                )
                if res.get("ok"):
                    rows_acc.append(
                        {
                            "Config": cfg_path.name,
                            "Estrategia": res["strategy"],
                            "TF": res.get("timeframe", tf),
                            "Par": res.get("symbol", f"BTC/{q}"),
                            "Retorno": res["net_profit_pct"],
                            "PF": res["profit_factor"],
                            "Max DD": res["max_drawdown_pct"],
                            "Trades": res["total_trades"],
                            "Sharpe": res.get("sharpe_ratio"),
                        }
                    )
                else:
                    errors_acc.append(f"{cfg_path.name} ({tf}, BTC/{q}): {res.get('error', 'falha')}")
    progress.progress(1.0, text="Concluido!")
    st.session_state["backtest_all_rows"] = rows_acc
    st.session_state["backtest_all_errors"] = errors_acc


def _download_matrix(
    project_root: Path,
    *,
    timeframes: list[str],
    quotes: list[str],
    force: bool = False,
) -> list[dict]:
    results: list[dict] = []
    for q in quotes:
        for tf in timeframes:
            res = run_download(
                project_root,
                "config/backtest.yaml",
                force=force,
                timeframe=tf,
                quote=q,
            )
            results.append(res)
    return results


def _show_batch_results() -> None:
    rows = st.session_state.get("backtest_all_rows")
    if rows:
        df = pd.DataFrame(rows).sort_values("Retorno", ascending=False)
        fmt = df.copy()
        if "Par" in fmt.columns and "TF" in fmt.columns:
            fmt = fmt.sort_values(["Par", "TF", "Retorno"], ascending=[True, True, False])
        fmt["Retorno"] = fmt["Retorno"].apply(lambda x: f"{x:.1%}")
        fmt["Max DD"] = fmt["Max DD"].apply(lambda x: f"{x:.1%}")
        st.dataframe(fmt, use_container_width=True, hide_index=True)
        st.success(
            f"{len(rows)} backtests concluidos. Va em **Comparar** ou **ATLAS Intelligence** "
            f"para baixar o relatorio comparativo de todos."
        )
    errs = st.session_state.get("backtest_all_errors")
    if errs:
        for e in errs:
            st.warning(e)


def _show_download_result(res: dict, project_root: Path) -> None:
    if not res.get("ok"):
        st.error(res.get("error", "Falha no download"))
        return
    src = "cache local (ja existia)" if res.get("from_cache") else "Binance API (baixado agora)"
    rel = Path(res["cache_file"]).relative_to(project_root) if res.get("cache_file") else res.get("cache_dir")
    st.success(
        f"**{res['candles']}** candles · {res['symbol']} {res['timeframe']} · fonte: {src}"
    )
    st.code(str(rel), language="text")
    if res.get("db_rows"):
        st.info(f"PostgreSQL: ate {res['db_rows']} linhas inseridas.")
    st.caption("Pasta completa: `data/cache/` dentro do projeto Quantum Trend.")


def render_research(project_root: Path) -> None:
    _init_research_state()
    st.markdown("## Pesquisa")
    st.caption("Backtest e analise — escolha timeframe e moeda (USDT/USDC).")

    configs = list_config_files(project_root)
    if not configs:
        st.error("Nenhum config/backtest*.yaml encontrado.")
        return

    st.markdown("### Configuracao dos testes")

    st.radio(
        "Timeframe do backtest",
        options=["4h", "1d", "both"],
        format_func=lambda x: {
            "4h": "4 horas (4h)",
            "1d": "1 dia (1d)",
            "both": "4h e 1d (testar os dois)",
        }[x],
        horizontal=True,
        key="research_tf_mode",
        help="Em 'ambos', cada estrategia roda em 4h e 1d.",
    )

    st.checkbox(
        "Testar USDT e USDC juntos",
        value=True,
        key="research_both_quotes",
        help="Marcado: cada estrategia roda em BTC/USDT e BTC/USDC. Desmarque para testar apenas uma moeda.",
    )
    if not st.session_state.get("research_both_quotes", True):
        st.selectbox(
            "Moeda (quote)",
            QUOTE_ASSETS,
            key="research_quote_single",
        )

    tfs, quotes = _research_opts()
    tf_label = " + ".join(tfs) if len(tfs) > 1 else tfs[0]
    quote_label = " + ".join(quotes) if len(quotes) > 1 else quotes[0]
    total_runs = len(configs) * len(tfs) * len(quotes)
    st.info(
        f"Testes em **BTC/{quote_label}** · timeframe(s): **{tf_label}**. "
        f"Baixe os dados antes do backtest (USDT e USDC usam caches separados)."
    )

    dl_c1, dl_c2 = st.columns(2)
    with dl_c1:
        if st.button("Baixar dados selecionados", use_container_width=True, key="btn_dl_selected"):
            with st.spinner("Baixando..."):
                results = _download_matrix(project_root, timeframes=tfs, quotes=quotes)
            st.session_state["last_download_results"] = results
            if results:
                st.session_state["last_download_result"] = results[-1]
    with dl_c2:
        if st.button("Baixar USDT+USDC (4h e 1d)", use_container_width=True, key="btn_dl_all"):
            with st.spinner("Baixando todos os pares..."):
                results = _download_matrix(
                    project_root,
                    timeframes=["4h", "1d"],
                    quotes=list(QUOTE_ASSETS),
                )
            st.session_state["last_download_results"] = results
            if results:
                st.session_state["last_download_result"] = results[-1]

    last_results = st.session_state.get("last_download_results")
    if last_results:
        ok = sum(1 for r in last_results if r.get("ok"))
        st.caption(f"Ultimo lote: {ok}/{len(last_results)} downloads OK.")
        for res in last_results:
            if res.get("ok"):
                st.write(f"✓ {res['symbol']} {res['timeframe']} — {res['candles']} candles")
            else:
                st.write(f"✗ {res.get('symbol', '?')} — {res.get('error', 'falha')}")

    last_dl = st.session_state.get("last_download_result")
    if last_dl and not last_results:
        _show_download_result(last_dl, project_root)

    st.markdown("### Arquivos de cache no disco")
    cache_dir = project_root / "data" / "cache"
    if cache_dir.is_dir():
        files = sorted(cache_dir.glob("*.parquet"))
        if files:
            for f in files:
                kb = f.stat().st_size / 1024
                st.write(f"`{f.name}` — {kb:.0f} KB")
        else:
            st.caption("Nenhum arquivo em data/cache ainda.")
    else:
        st.caption("Pasta data/cache sera criada no primeiro download.")

    st.markdown("### Teste em lote")
    st.caption(
        f"{len(configs)} estrategias × {len(tfs)} TF × {len(quotes)} quote(s) = ate **{total_runs}** backtests"
    )
    if st.button("Rodar TODAS as estrategias", type="primary", key="btn_bt_all_top"):
        _run_batch_backtest(project_root, configs)
        st.rerun()

    _show_batch_results()
    st.divider()

    config_labels = [c.name for c in configs]
    default_idx = next((i for i, c in enumerate(configs) if c.name == "backtest_mm200_v2.yaml"), 0)
    quote_single = quotes[0] if len(quotes) == 1 else "USDT"

    tab_dl, tab_bt, tab_all, tab_cmp, tab_wf = st.tabs(
        ["Baixar dados", "Backtest", "Testar todas", "Comparar", "Walk-forward"]
    )

    with tab_dl:
        st.markdown("### Baixar candles historicos")
        cfg_dl = st.selectbox("Config de dados", config_labels, index=default_idx, key="dl_cfg")
        q_dl = st.selectbox("Quote", QUOTE_ASSETS, key="dl_quote")
        tf_dl = st.radio(
            "Timeframe download",
            ["4h", "1d"],
            horizontal=True,
            key="dl_tf",
        )
        force = st.checkbox("Forcar re-download", key="dl_force")
        to_db = st.checkbox("Salvar no PostgreSQL", key="dl_db")
        if st.button("Baixar dados", type="primary", key="btn_dl"):
            with st.spinner(f"Baixando BTC/{q_dl} {tf_dl}..."):
                res = run_download(
                    project_root,
                    f"config/{cfg_dl}",
                    force=force,
                    to_db=to_db,
                    timeframe=tf_dl,
                    quote=q_dl,
                )
            st.session_state["last_download_result"] = res
        if st.session_state.get("last_download_result"):
            _show_download_result(st.session_state["last_download_result"], project_root)

    with tab_bt:
        st.markdown("### Rodar backtest")
        cfg_bt = st.selectbox("Config backtest", config_labels, index=default_idx, key="bt_cfg")
        q_bt = st.selectbox("Quote", QUOTE_ASSETS, key="bt_quote")
        tf_bt = st.radio("Timeframe", ["4h", "1d"], horizontal=True, key="bt_tf")
        if st.button("Executar backtest", type="primary", key="btn_bt"):
            with st.spinner(f"Rodando backtest BTC/{q_bt} {tf_bt}..."):
                res = run_backtest_dashboard(
                    project_root,
                    f"config/{cfg_bt}",
                    timeframe=tf_bt,
                    quote=q_bt,
                )
            if res.get("ok"):
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Retorno", f"{res['net_profit_pct']:.1%}")
                m2.metric("Profit Factor", f"{res['profit_factor']:.2f}")
                m3.metric("Max DD", f"{res['max_drawdown_pct']:.1%}")
                m4.metric("Trades", res["total_trades"])
                st.caption(
                    f"{res['symbol']} {res['timeframe']} · "
                    f"Buy & Hold: {res['buy_hold_pct']:.1%} · "
                    f"Win rate: {res['win_rate']:.1%} · "
                    f"Sharpe: {res.get('sharpe_ratio') or 'N/A'}"
                )
                st.success(f"Relatorio salvo: `{res['report_path']}`")
                st.info("Va em **ATLAS Intelligence** ou **Paper Trading** para operar.")
            else:
                st.error(res.get("error", "Falha"))

    with tab_all:
        st.markdown("### Testar todas as estrategias")
        st.caption(
            f"Usa timeframe(s): **{tf_label}** · quote(s): **{quote_label}**"
        )
        if st.button("Rodar todas as estrategias", type="primary", key="btn_bt_all"):
            _run_batch_backtest(project_root, configs)
            st.rerun()
        _show_batch_results()

    with tab_cmp:
        st.markdown("### Exportar todos os relatorios")
        st.caption(
            "Gera **1 relatorio unico** com todas as estrategias (para colar em IA), "
            "mais ZIP e downloads separados se quiser."
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("EXPORTAR TODOS (.zip)", type="primary", key="btn_export_all"):
                with st.spinner("Gerando relatorios (pode levar 1-2 min)..."):
                    st.session_state["export_result"] = run_export_all_reports(project_root)
                st.rerun()
        with c2:
            if st.button("Atualizar ranking na tela", key="btn_cmp"):
                with st.spinner("Analisando..."):
                    st.session_state["compare_rows"] = run_compare(project_root)
                st.rerun()

        export = st.session_state.get("export_result")
        if export:
            show_export_result(project_root, export, key_prefix="research_export")

        res = st.session_state.get("compare_rows")
        if res and res.get("ok"):
            st.markdown("#### Ranking")
            df = pd.DataFrame(res["rows"])
            if "Retorno" in df.columns:
                df["Retorno"] = df["Retorno"].apply(lambda x: f"{x:.1%}" if x is not None else "N/A")
            if "DD" in df.columns:
                df["DD"] = df["DD"].apply(lambda x: f"{x:.1%}" if x is not None else "N/A")
            st.dataframe(df, use_container_width=True, hide_index=True)
        elif not export:
            st.info("Clique em **EXPORTAR TODOS** apos rodar os backtests.")

    with tab_wf:
        st.markdown("### Walk-forward (IS/OOS)")
        cfg_wf = st.selectbox("Config", config_labels, index=default_idx, key="wf_cfg")
        q_wf = st.selectbox("Quote", QUOTE_ASSETS, key="wf_quote")
        tf_wf = st.radio("Timeframe", ["4h", "1d"], horizontal=True, key="wf_tf")
        train_pct = st.slider("In-sample %", 0.50, 0.90, 0.70, 0.05, key="wf_pct")
        if st.button("Executar walk-forward", type="primary", key="btn_wf"):
            with st.spinner(f"Walk-forward BTC/{q_wf} {tf_wf}..."):
                res = run_walkforward(
                    project_root,
                    f"config/{cfg_wf}",
                    train_pct=train_pct,
                    timeframe=tf_wf,
                    quote=q_wf,
                )
            st.session_state["wf_result"] = res

        res = st.session_state.get("wf_result")
        if res and res.get("ok"):
            w1, w2, w3 = st.columns(3)
            w1.metric("IS retorno", f"{res['is_return']:.1%}")
            w2.metric("OOS retorno", f"{res['oos_return']:.1%}")
            wfe = res.get("wfe")
            w3.metric("WFE", f"{wfe:.0%}" if wfe is not None else "N/A")
            st.caption(
                f"Split: {res['split_timestamp']} · "
                f"OOS PF: {res['oos_pf']:.2f} · "
                f"Trades IS/OOS: {res['is_trades']}/{res['oos_trades']}"
            )
            st.success(f"Salvo: `{res['path']}`")
