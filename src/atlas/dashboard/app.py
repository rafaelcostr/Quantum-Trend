"""ATLAS QUANT — live trading dashboard."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from atlas.core.config import load_config  # noqa: E402
from atlas.core.env import load_project_env  # noqa: E402
from atlas.dashboard.charts_plotly import build_performance_charts, build_price_chart  # noqa: E402
from atlas.dashboard.charts_tv import render_tradingview_chart  # noqa: E402
from atlas.dashboard.performance import compute_performance, extract_trade_markers  # noqa: E402
from atlas.dashboard.service import DashboardService, load_journal_events  # noqa: E402
from atlas.dashboard.intelligence_ui import render_level1  # noqa: E402
from atlas.intelligence.analyzer import analyze_path  # noqa: E402
from atlas.intelligence.metrics import discover_reports  # noqa: E402
from atlas.monitoring.alerts import TelegramAlerts  # noqa: E402


def _signal_color(signal: str) -> str:
    if signal == "enter_long":
        return "#3fb950"
    if signal == "exit_long":
        return "#f85149"
    return "#8b949e"


def main() -> None:
    load_project_env(PROJECT_ROOT)
    config_env = os.getenv("ATLAS_CONFIG")
    config_path = Path(config_env) if config_env else PROJECT_ROOT / "config" / "paper.yaml"
    config = load_config(config_path)
    service = DashboardService(config)
    alerts = TelegramAlerts()

    st.set_page_config(
        page_title="ATLAS QUANT",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .block-container { padding-top: 1rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.title("ATLAS QUANT")
        page = st.radio("Seção", ["Trading ao Vivo", "ATLAS Intelligence"], index=0)
        st.caption(f"**{config.mode.value}** · {config.exchange.symbol} {config.exchange.timeframe}")
        st.write(f"Estratégia ativa: `{config.strategy.name}`")

        if page == "Trading ao Vivo":
            refresh = st.slider("Atualizar (seg)", 15, 300, 60, 15)
            bars = st.slider("Barras no gráfico", 60, 300, 120, 10)
            chart_engine = st.radio("Motor do gráfico", ["TradingView", "Plotly"], index=0)
            auto = st.toggle("Auto-refresh", value=True)
        else:
            refresh = 0
            bars = 120
            chart_engine = "TradingView"
            auto = False
            report_paths = discover_reports(PROJECT_ROOT / "data" / "reports")
            report_labels = [p.stem.replace("_report", "") for p in report_paths]
            selected_strategy = (
                st.selectbox("Estratégia (backtest)", report_labels)
                if report_labels
                else None
            )

        st.divider()
        st.subheader("Alertas Telegram")
        if alerts.enabled:
            st.success("Telegram configurado")
            if st.button("Testar Telegram"):
                ok = alerts.send("✅ ATLAS QUANT — teste de alerta OK")
                st.success("Enviado!" if ok else "Falhou — verifique token/chat_id")
        else:
            st.warning("Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env")

        if st.button("Atualizar agora", use_container_width=True):
            st.rerun()

    if page == "ATLAS Intelligence":
        if not report_paths:
            st.warning("Nenhum relatório em data/reports/. Rode: `atlas research backtest`")
            st.stop()
        sel_path = next(p for p in report_paths if p.stem.replace("_report", "") == selected_strategy)
        analysis = analyze_path(sel_path, market=config.exchange.symbol, timeframe=config.exchange.timeframe)
        render_level1(analysis)
        st.stop()

    # --- Trading ao Vivo ---
    try:
        state = service.get_live_state()
        df = service.fetch_candles_df()
        events = load_journal_events(config.database_url, config.mode.value, limit=500)
        markers = extract_trade_markers(events)
        perf = compute_performance(
            events,
            initial_capital=config.risk.initial_capital,
            current_equity=state.equity_usdt,
        )
    except Exception as exc:
        st.error(f"Erro ao carregar dados: {exc}")
        st.stop()

    # KPI row
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("USDT livre", f"${state.usdt_free:,.2f}")
    c2.metric("BTC", f"{state.btc_total:.6f}")
    c3.metric("Equity", f"${state.equity_usdt:,.2f}")
    c4.metric("PnL", f"${perf.net_pnl:,.2f}", f"{perf.net_pnl_pct:.2%}")
    c5.metric("Max DD", f"{perf.max_drawdown_pct:.2%}")
    c6.metric("Preço", f"${state.last_close:,.2f}")
    c7.metric("Sinal", state.signal.replace("_", " ").upper(), state.reason[:30], delta_color="off")

    mm200_txt = f"{state.mm200:,.2f}" if state.mm200 is not None else "—"
    rsi_txt = f"{state.rsi:.1f}" if state.rsi is not None else "—"
    adx_txt = f"{state.adx:.1f}" if state.adx is not None else "—"
    st.markdown(
        f"""
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;">
          <span style="background:#21262d;padding:5px 10px;border-radius:6px;">MM200: <b>{mm200_txt}</b></span>
          <span style="background:#21262d;padding:5px 10px;border-radius:6px;">RSI: <b>{rsi_txt}</b></span>
          <span style="background:#21262d;padding:5px 10px;border-radius:6px;">ADX: <b>{adx_txt}</b></span>
          <span style="background:#21262d;padding:5px 10px;border-radius:6px;color:{_signal_color(state.signal)};">
            {'LONG BTC' if state.in_position else 'FLAT'}
          </span>
          <span style="background:#21262d;padding:5px 10px;border-radius:6px;">
            Trades: <b>{perf.trade_count}</b>
          </span>
          <span style="background:#21262d;padding:5px 10px;border-radius:6px;">
            {state.last_time.strftime('%Y-%m-%d %H:%M UTC')}
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_chart, tab_perf, tab_journal = st.tabs(["Gráfico ao vivo", "PnL & Drawdown", "Journal"])

    with tab_chart:
        if chart_engine == "TradingView":
            render_tradingview_chart(df, markers, bars=bars)
        else:
            st.plotly_chart(build_price_chart(df, markers, bars=bars), use_container_width=True)

    with tab_perf:
        eq_fig, dd_fig = build_performance_charts(perf)
        p1, p2 = st.columns(2)
        with p1:
            st.plotly_chart(eq_fig, use_container_width=True)
        with p2:
            st.plotly_chart(dd_fig, use_container_width=True)
        st.caption(
            f"Capital inicial (config): ${perf.initial_capital:,.2f} · "
            f"Pico equity: ${perf.peak_equity:,.2f}"
        )

    with tab_journal:
        if events:
            rows = []
            for ev in events:
                payload = ev.get("payload") or {}
                detail = (
                    payload.get("signal")
                    or payload.get("reason")
                    or payload.get("error")
                    or payload.get("action")
                    or ""
                )
                if payload.get("equity"):
                    detail = f"{detail} | equity=${float(payload['equity']):,.2f}"
                rows.append({"hora": ev.get("ts"), "evento": ev.get("event"), "detalhe": str(detail)[:100]})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Sem eventos. Rode `atlas trade paper` em outro terminal.")

        st.markdown("**Setup**")
        st.code("atlas trade paper   # terminal 1\natlas dashboard     # terminal 2", language="bash")

    st.caption(f"Atualizado: {state.updated_at.strftime('%H:%M:%S UTC')}")

    if auto:
        time.sleep(refresh)
        st.rerun()


if __name__ == "__main__":
    main()
