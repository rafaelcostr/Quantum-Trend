"""Painel de saldo Binance Demo — visivel no dashboard."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from atlas.brokers.binance import credentials_configured
from atlas.dashboard.actions import run_trade_check


def render_demo_balance_panel(project_root: Path, paper_config_rel: str, *, compact: bool = False) -> None:
    """Mostra saldo demo e botao para testar API."""
    has_keys = credentials_configured(live=False)
    env_path = project_root / ".env"

    if not compact:
        st.markdown("### Saldo Binance Demo")

    if not env_path.is_file():
        st.error(f"Arquivo `.env` nao encontrado em: `{env_path}`")
        st.code("copy .env.example .env", language="powershell")
        return

    if not has_keys:
        st.warning(
            "Chaves demo nao configuradas. Edite o `.env` na pasta do projeto e preencha:\n\n"
            "`BINANCE_DEMO_API_KEY=...`\n\n"
            "`BINANCE_DEMO_API_SECRET=...`\n\n"
            "Crie as chaves em **demo.binance.com** (nao e binance.com)."
        )
    elif st.session_state.get("demo_balance_result") is None:
        with st.spinner("Buscando saldo demo..."):
            st.session_state["demo_balance_result"] = run_trade_check(project_root, paper_config_rel)

    if st.button("Atualizar saldo Demo", type="primary", key=f"demo_bal_{compact}"):
        with st.spinner("Conectando na Binance Demo..."):
            res = run_trade_check(project_root, paper_config_rel)
        st.session_state["demo_balance_result"] = res

    res = st.session_state.get("demo_balance_result")
    if not res:
        if not compact:
            st.caption("Clique no botao acima para buscar USDT e BTC da conta demo.")
        return

    if res.get("ok"):
        usdt = res.get("usdt_free", 0)
        st.success(f"Conectado — USDT livre: **${usdt:,.2f}**")
        c1, c2, c3 = st.columns(3)
        c1.metric("USDT Demo", f"${usdt:,.2f}")
        c2.metric("Status API", "OK")
        c3.metric("BTC 4H", f"${res.get('last_close', 0):,.2f}" if res.get("last_close") else "—")
        st.caption(
            "Esse saldo aparece automaticamente em **Trading ao Vivo** "
            "(USDT livre / Equity) depois que as chaves estao no .env."
        )
    else:
        st.error(res.get("error", "Falha na conexao"))
        for label, key in [
            ("Arquivo .env", "env_file"),
            ("API Key", "api_key_ok"),
            ("Secret", "secret_ok"),
        ]:
            val = res.get(key)
            if key == "env_file":
                st.write(f"**{label}:** {'OK' if val else 'Faltando'}")
            else:
                st.write(f"**{label}:** {'OK' if val else 'Faltando'}")
        if res.get("public_ip"):
            st.write(f"**Seu IP (whitelist):** `{res['public_ip']}`")
        st.markdown(
            "Checklist: chave em [demo.binance.com](https://demo.binance.com) · "
            "IP na whitelist · permissao Spot + Leitura"
        )
