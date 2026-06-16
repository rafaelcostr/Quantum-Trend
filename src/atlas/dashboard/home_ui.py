"""Dashboard — pagina inicial com visao geral."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from atlas.core.config import AtlasConfig
from atlas.dashboard.bot_manager import bot_status
from atlas.intelligence.metrics import discover_reports
from atlas.monitoring.alerts import TelegramAlerts


def render_home(project_root: Path, config: AtlasConfig) -> None:
    st.markdown("## ATLAS QUANT")
    st.caption("Centro de controle — pesquisa, paper trading e monitoramento.")

    status = bot_status()
    alerts = TelegramAlerts()
    reports = discover_reports(project_root / "data/reports")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Modo", config.mode.value.upper())
    c2.metric("Bot paper", "Ativo" if status.get("running") else "Parado")
    c3.metric("Relatorios", len(reports))
    c4.metric("Telegram", "OK" if alerts.enabled else "Off")

    st.markdown("---")
    st.markdown("### Fluxo recomendado")

    steps = [
        ("1. Pesquisa", "Baixar dados → Backtest → Comparar estrategias", "Pesquisa"),
        ("2. Intelligence", "Ver Atlas Score, diagnostico L2/L3, walk-forward", "ATLAS Intelligence"),
        ("3. Paper", "Validar API → Iniciar bot 24/7", "Paper Trading"),
        ("4. Monitorar", "Graficos, PnL, journal ao vivo", "Trading ao Vivo"),
    ]
    for title, desc, page in steps:
        st.markdown(f"**{title}** — {desc}  →  sidebar: *{page}*")

    if not status.get("running"):
        st.info("Paper parado. Va em **Paper Trading** e clique em **Iniciar bot 24/7**.")
    else:
        st.success(f"Bot rodando (PID {status.get('pid')}). Acompanhe em **Trading ao Vivo**.")

    st.markdown("---")
    st.caption(f"Estrategia: `{config.strategy.name}` · {config.exchange.symbol} {config.exchange.timeframe}")
