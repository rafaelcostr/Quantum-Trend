"""Dashboard — Operacao paper (check, bot, tick unico)."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from atlas.core.config import AtlasConfig
from atlas.core.models import TradingMode
from atlas.dashboard.actions import run_paper_once, run_trade_check, run_backtest_config
from atlas.dashboard.bot_manager import bot_status, start_bot, stop_bot, tail_log
from atlas.dashboard.demo_balance_ui import render_demo_balance_panel
from atlas.dashboard.ops_context import get_ops_config, set_ops_config
from atlas.dashboard.strategy_config import save_active_config


def render_paper(project_root: Path, paper_config_rel: str) -> None:
    config = get_ops_config(project_root, paper_config_rel)
    st.markdown("## Paper Trading")
    st.caption(
        f"Binance Demo — `{config.strategy.name}` · {config.exchange.symbol} "
        f"{config.exchange.timeframe}"
    )

    render_demo_balance_panel(project_root, paper_config_rel, config=config)
    st.divider()

    status = bot_status()
    c1, c2, c3 = st.columns(3)
    with c1:
        if status.get("running"):
            st.success(f"Bot ATIVO — PID {status.get('pid')}")
        else:
            st.info("Bot parado")
    with c2:
        st.metric("Par", config.exchange.symbol)
    with c3:
        if status.get("started_at"):
            st.caption(f"Iniciado: {status['started_at'][:19]}")

    tab_ctrl, tab_check, tab_log = st.tabs(["Controle", "Validar API", "Log do bot"])

    with tab_ctrl:
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("Iniciar bot 24/7", type="primary", use_container_width=True, disabled=status.get("running")):
                active_rel = save_active_config(project_root, config)
                res = start_bot(project_root, active_rel)
                if res.get("ok"):
                    st.success(f"{res['message']} · {config.strategy.name}")
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
                with st.spinner("Avaliando ultimo candle..."):
                    res = run_paper_once(config)
                if res.get("warning"):
                    st.warning(res["warning"])
                if res.get("ok"):
                    st.json(res["outcome"])
                else:
                    st.error(res.get("error", "Falha"))

        st.markdown("---")
        if st.button("Testar estrategia (backtest rapido)", use_container_width=True, key="btn_quick_bt"):
            bt_cfg = config.model_copy(deep=True)
            bt_cfg.mode = TradingMode.BACKTEST
            with st.spinner(f"Backtest {config.exchange.symbol} {config.exchange.timeframe}..."):
                bt = run_backtest_config(project_root, bt_cfg)
            if bt.get("ok"):
                st.success(
                    f"Retorno {bt['net_profit_pct']:.1%} · PF {bt['profit_factor']:.2f} · "
                    f"{bt['total_trades']} trades · DD {bt['max_drawdown_pct']:.1%}"
                )
                st.caption(f"Relatorio: `{bt['report_path']}`")
            else:
                st.error(bt.get("error", "Falha no backtest"))

        st.markdown(
            "**Como funciona:** escolha estrategia, moeda (USDT/USDC) e timeframe na sidebar. "
            "Clique **Salvar config operacional** antes de iniciar o bot. "
            "Acompanhe em **Trading ao Vivo** e **Historico Demo**."
        )

    with tab_check:
        st.markdown("### Validar Binance Demo")
        if st.button("Testar conexao", type="primary", key="btn_check"):
            with st.spinner("Testando API..."):
                res = run_trade_check(project_root, paper_config_rel, ops_config=config)
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
                ("Par", res.get("symbol", config.exchange.symbol)),
                ("IP publico", res.get("public_ip") or "N/A"),
                ("Candles publicos", res.get("ohlcv", "N/A")),
                ("Saldo privado", res.get("balance", "N/A")),
                ("USDT livre", f"${res.get('usdt_free', 0):,.2f}" if res.get("usdt_free") is not None else "N/A"),
                ("USDC livre", f"${res.get('usdc_free', 0):,.2f}" if res.get("usdc_free") is not None else "N/A"),
                ("Quote ativo", res.get("quote_free", "N/A")),
                ("BTC ultimo", res.get("last_close", "N/A")),
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
