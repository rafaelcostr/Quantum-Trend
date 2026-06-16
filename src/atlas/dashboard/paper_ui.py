"""Dashboard — Operacao paper (check, bot, tick unico)."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from atlas.core.config import load_config
from atlas.dashboard.actions import run_paper_once, run_trade_check
from atlas.dashboard.bot_manager import bot_status, start_bot, stop_bot, tail_log


def render_paper(project_root: Path, paper_config_rel: str) -> None:
    st.markdown("## Paper Trading")
    st.caption("Binance Demo — controle do bot e validacao da API.")

    status = bot_status()
    c1, c2, c3 = st.columns(3)
    with c1:
        if status.get("running"):
            st.success(f"Bot ATIVO — PID {status.get('pid')}")
        else:
            st.info("Bot parado")
    with c2:
        st.metric("Config", paper_config_rel)
    with c3:
        if status.get("started_at"):
            st.caption(f"Iniciado: {status['started_at'][:19]}")

    tab_ctrl, tab_check, tab_log = st.tabs(["Controle", "Validar API", "Log do bot"])

    with tab_ctrl:
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("Iniciar bot 24/7", type="primary", use_container_width=True, disabled=status.get("running")):
                res = start_bot(project_root, paper_config_rel)
                if res.get("ok"):
                    st.success(res["message"])
                else:
                    st.warning(res["message"])
                st.rerun()
        with col_b:
            if st.button("Parar bot", use_container_width=True, disabled=not status.get("running")):
                res = stop_bot()
                st.success(res["message"])
                st.rerun()
        with col_c:
            if st.button("Um ciclo (tick)", use_container_width=True):
                config = load_config(project_root / paper_config_rel)
                with st.spinner("Avaliando ultimo candle..."):
                    res = run_paper_once(config)
                if res.get("warning"):
                    st.warning(res["warning"])
                if res.get("ok"):
                    st.json(res["outcome"])
                else:
                    st.error(res.get("error", "Falha"))

        st.markdown("---")
        st.markdown(
            "**Como funciona:** o bot avalia a cada ~2 min (config `poll_seconds`). "
            "Inicie aqui e acompanhe em **Trading ao Vivo**."
        )

    with tab_check:
        st.markdown("### Validar Binance Demo")
        if st.button("Testar conexao", type="primary", key="btn_check"):
            with st.spinner("Testando API..."):
                res = run_trade_check(project_root, paper_config_rel)
            st.session_state["check_result"] = res

        res = st.session_state.get("check_result")
        if res:
            if res.get("ok"):
                st.success("Conexao OK — pronto para paper trading")
            else:
                st.error(res.get("error", "Falha na conexao"))

            rows = [
                ("Arquivo .env", "OK" if res.get("env_file") else "Faltando"),
                ("API Key", "OK" if res.get("api_key_ok") else "Faltando"),
                ("Secret", "OK" if res.get("secret_ok") else "Faltando"),
                ("IP publico", res.get("public_ip") or "N/A"),
                ("Candles publicos", res.get("ohlcv", "N/A")),
                ("Saldo privado", res.get("balance", "N/A")),
                ("USDT livre", f"${res.get('usdt_free', 0):,.2f}" if res.get("usdt_free") is not None else "N/A"),
                ("BTC ultimo 4H", res.get("last_close", "N/A")),
            ]
            for label, val in rows:
                st.write(f"**{label}:** {val}")

            if not res.get("ok"):
                st.markdown(
                    """
                    **Erro -2015:** chave criada em [demo.binance.com](https://demo.binance.com),
                    IP na whitelist, permissoes Leitura + Spot (sem saques).
                    """
                )

    with tab_log:
        st.markdown("### Ultimas linhas do bot")
        if st.button("Atualizar log", key="btn_log"):
            st.rerun()
        st.code(tail_log(50), language="text")
