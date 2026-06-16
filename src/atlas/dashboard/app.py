"""ATLAS QUANT — dashboard unificado (pesquisa, paper, trading, intelligence)."""
from __future__ import annotations

import os
import sys
import time
from datetime import timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

_APP_PATH = Path(__file__).resolve()
SRC_ROOT = _APP_PATH.parents[2]
PROJECT_ROOT = _APP_PATH.parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Forca recarregar actions (Streamlit cacheia modulos antigos)
import importlib
import atlas.dashboard.actions as _actions_mod

importlib.reload(_actions_mod)

from atlas.core.env import find_project_root, load_project_env  # noqa: E402

PROJECT_ROOT = find_project_root(PROJECT_ROOT)
load_project_env(PROJECT_ROOT)

from atlas.core.config import load_config  # noqa: E402
from atlas.core.models import TradingMode  # noqa: E402
from atlas.dashboard.charts_plotly import build_performance_charts, build_price_chart  # noqa: E402
from atlas.dashboard.charts_tv import render_tradingview_chart  # noqa: E402
from atlas.dashboard.charts_tv_live import render_tradingview_live_chart  # noqa: E402
from atlas.dashboard.demo_balance_ui import render_demo_balance_panel  # noqa: E402
from atlas.dashboard.home_ui import render_home  # noqa: E402
from atlas.dashboard.intelligence_ui import render_intelligence  # noqa: E402
from atlas.dashboard.paper_ui import render_paper  # noqa: E402
from atlas.dashboard.performance import compute_performance, extract_trade_markers  # noqa: E402
from atlas.dashboard.research_ui import render_research  # noqa: E402
from atlas.dashboard.service import DashboardService, fetch_demo_balances, load_journal_events  # noqa: E402
from atlas.intelligence.analyzer import analyze_path  # noqa: E402
from atlas.intelligence.metrics import discover_reports  # noqa: E402
from atlas.monitoring.alerts import TelegramAlerts  # noqa: E402

from atlas.dashboard.ops_context import set_ops_config  # noqa: E402
from atlas.dashboard.strategy_config import (  # noqa: E402
    QUOTE_ASSETS,
    TIMEFRAMES,
    build_operational_config,
    list_strategy_names,
    save_active_config,
)
from atlas.dashboard.trades_history_ui import render_trades_history  # noqa: E402

PAGES = [
    "Inicio",
    "Pesquisa",
    "Paper Trading",
    "Trading ao Vivo",
    "Historico Demo",
    "ATLAS Intelligence",
]

OPS_PAGES = {"Paper Trading", "Trading ao Vivo", "Historico Demo"}

CHART_LIVE = "Ao vivo (WebSocket)"
CHART_STATIC = "Estatico (refresh)"
CHART_PLOTLY = "Plotly"


def _signal_color(signal: str) -> str:
    if signal == "enter_long":
        return "#3fb950"
    if signal == "exit_long":
        return "#f85149"
    return "#8b949e"


@st.cache_data(ttl=120, show_spinner=False)
def _cached_candles_df(strategy: str, symbol: str, timeframe: str) -> pd.DataFrame:
    quote = symbol.split("/")[-1].upper()
    config = build_operational_config(
        PROJECT_ROOT,
        strategy_name=strategy,
        quote_asset=quote,
        timeframe=timeframe,
    )
    service = DashboardService(config)
    limit = 400 if timeframe == "1d" else 280
    return service.fetch_candles_df(limit=limit)


@st.cache_data(ttl=90, show_spinner=False)
def _cached_demo_balances(strategy: str, symbol: str, timeframe: str) -> tuple[dict[str, float] | None, str | None]:
    load_project_env(PROJECT_ROOT)
    quote = symbol.split("/")[-1].upper()
    config = build_operational_config(
        PROJECT_ROOT,
        strategy_name=strategy,
        quote_asset=quote,
        timeframe=timeframe,
    )
    return fetch_demo_balances(config)


def _load_trading_balance_state(config, service, ind_df, events):
    balances, balance_error = _cached_demo_balances(
        config.strategy.name,
        config.exchange.symbol,
        config.exchange.timeframe,
    )
    state = service.get_live_state(
        ind_df=ind_df,
        balances=balances,
        balance_error=balance_error,
    )
    perf = compute_performance(
        events,
        initial_capital=config.risk.initial_capital,
        current_equity=state.equity_usdt,
    )
    return state, perf


def _fetch_and_render_trading_balance(
    config,
    service,
    ind_df,
    events,
    *,
    paper_config_rel: str,
) -> tuple | None:
    with st.spinner("Carregando saldo demo..."):
        try:
            state, perf = _load_trading_balance_state(config, service, ind_df, events)
        except Exception as exc:
            st.error(f"Erro ao carregar saldo: {exc}")
            return None

    if state.balance_error:
        st.warning(state.balance_error)
        render_demo_balance_panel(PROJECT_ROOT, paper_config_rel, compact=True, config=config)
        return None

    _render_trading_metrics(state, perf, balance_unavailable=False)
    return state, perf

def _render_trading_panels(
    state,
    perf,
    events,
    *,
    paper_config_rel: str,
    balance_error: bool,
) -> None:
    if balance_error:
        return

    tab_perf, tab_journal = st.tabs(["PnL & Drawdown", "Journal"])

    with tab_perf:
        eq_fig, dd_fig = build_performance_charts(perf)
        p1, p2 = st.columns(2)
        with p1:
            st.plotly_chart(eq_fig, use_container_width=True)
        with p2:
            st.plotly_chart(dd_fig, use_container_width=True)

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
                rows.append(
                    {"hora": ev.get("ts"), "evento": ev.get("event"), "detalhe": str(detail)[:100]}
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Sem eventos ainda. Inicie o bot em **Paper Trading**.")

    st.caption(f"Atualizado: {state.updated_at.strftime('%H:%M:%S UTC')}")


def _render_trading_metrics(state, perf, *, balance_unavailable: bool = False) -> None:
    st.markdown("### Carteira & performance")

    quote_label = "Quote livre"
    if balance_unavailable:
        pnl_txt, pnl_delta = "N/A", None
        eq_txt = "N/A"
        usdt_txt = "N/A"
        btc_txt = "N/A"
        dd_txt = "N/A"
    else:
        pnl_txt = f"${perf.net_pnl:,.2f}"
        pnl_delta = f"{perf.net_pnl_pct:.2%}"
        eq_txt = f"${state.equity_usdt:,.2f}"
        quote_label = f"{state.quote_asset} livre"
        usdt_txt = f"${state.quote_free:,.2f}"
        btc_txt = f"{state.btc_total:.6f}"
        dd_txt = f"{perf.max_drawdown_pct:.2%}"

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric(quote_label, usdt_txt)
    c2.metric("BTC", btc_txt)
    c3.metric("Equity", eq_txt)
    c4.metric("PnL", pnl_txt, pnl_delta, delta_color="off")
    c5.metric("Max DD", dd_txt)
    c6.metric("Preco", f"${state.last_close:,.2f}")
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


def _render_trading(config, service, paper_config_rel, refresh, bars, chart_engine, auto) -> None:
    live_ws = chart_engine == CHART_LIVE

    try:
        events = load_journal_events(config.database_url, config.mode.value, limit=500)
        markers = extract_trade_markers(events)
        ind_df = _cached_candles_df(config.strategy.name, config.exchange.symbol, config.exchange.timeframe)
        chart_df = ind_df.tail(bars) if len(ind_df) > bars else ind_df
    except Exception as exc:
        st.error(f"Erro ao carregar grafico: {exc}")
        return

    if live_ws:
        render_tradingview_live_chart(
            chart_df,
            markers,
            symbol=config.exchange.symbol,
            timeframe=config.exchange.timeframe,
            bars=bars,
        )
        st.caption("Preco em tempo real via WebSocket Binance.")

        run_every = timedelta(seconds=refresh) if auto and refresh > 0 else None

        @st.fragment(run_every=run_every)
        def _live_balance_panel() -> None:
            result = _fetch_and_render_trading_balance(
                config,
                service,
                ind_df,
                events,
                paper_config_rel=paper_config_rel,
            )
            if result is None:
                return
            state, perf = result
            _render_trading_panels(
                state,
                perf,
                events,
                paper_config_rel=paper_config_rel,
                balance_error=False,
            )

        _live_balance_panel()
        return

    result = _fetch_and_render_trading_balance(
        config,
        service,
        ind_df,
        events,
        paper_config_rel=paper_config_rel,
    )
    if result is None:
        return
    state, perf = result

    tab_chart, tab_perf, tab_journal = st.tabs(["Grafico", "PnL & Drawdown", "Journal"])

    with tab_chart:
        df = chart_df if not chart_df.empty else ind_df
        if chart_engine == CHART_STATIC:
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
            st.info("Sem eventos ainda. Inicie o bot em **Paper Trading**.")

    st.caption(f"Atualizado: {state.updated_at.strftime('%H:%M:%S UTC')}")

    if auto and refresh > 0:
        time.sleep(refresh)
        st.rerun()


def main() -> None:
    load_project_env(PROJECT_ROOT)
    config_env = os.getenv("ATLAS_CONFIG")
    paper_config_rel = "config/paper.yaml"
    if config_env:
        p = Path(config_env)
        paper_config_rel = str(p.relative_to(PROJECT_ROOT)) if p.is_relative_to(PROJECT_ROOT) else str(p)
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
        page = st.radio("Menu", PAGES, index=0)

        refresh = 60
        bars = 120
        chart_engine = CHART_LIVE
        auto = True
        selected_strategy = None

        base_config = load_config(PROJECT_ROOT / paper_config_rel)
        ops_config = base_config

        if page in OPS_PAGES:
            st.divider()
            st.subheader("Operacoes")
            strategies = list_strategy_names(PROJECT_ROOT)
            prev = st.session_state.get("atlas_strategy", base_config.strategy.name)
            strat_idx = strategies.index(prev) if prev in strategies else 0
            op_strategy = st.selectbox("Estrategia", strategies, index=strat_idx, key="sb_strategy")
            prev_quote = st.session_state.get("atlas_quote", "USDT")
            op_quote = st.selectbox(
                "Moeda demo",
                QUOTE_ASSETS,
                index=QUOTE_ASSETS.index(prev_quote) if prev_quote in QUOTE_ASSETS else 0,
                key="sb_quote",
            )
            prev_tf = st.session_state.get("atlas_timeframe", base_config.exchange.timeframe)
            op_tf = st.selectbox(
                "Timeframe",
                TIMEFRAMES,
                index=TIMEFRAMES.index(prev_tf) if prev_tf in TIMEFRAMES else 0,
                key="sb_timeframe",
                help="4h = operacao padrao. 1d = graficos diarios.",
            )
            ops_config = build_operational_config(
                PROJECT_ROOT,
                strategy_name=op_strategy,
                quote_asset=op_quote,
                timeframe=op_tf,
                base_config_rel=paper_config_rel,
            )
            st.session_state["atlas_strategy"] = op_strategy
            st.session_state["atlas_quote"] = op_quote
            st.session_state["atlas_timeframe"] = op_tf
            set_ops_config(ops_config)

            if st.button("Salvar config operacional", use_container_width=True, key="btn_save_ops"):
                save_active_config(PROJECT_ROOT, ops_config)
                st.success(f"Salvo: {op_strategy} · BTC/{op_quote} · {op_tf}")

        config = ops_config
        service = DashboardService(config)
        st.caption(f"**{config.mode.value}** · {config.exchange.symbol} {config.exchange.timeframe}")
        st.write(f"Estrategia: `{config.strategy.name}`")

        if page == "Trading ao Vivo":
            chart_engine = st.radio(
                "Motor do grafico",
                [CHART_LIVE, CHART_STATIC, CHART_PLOTLY],
                index=0,
                help="Ao vivo: WebSocket Binance. Estatico: recarrega a pagina inteira.",
            )
            bars = st.slider("Barras no grafico", 60, 300, 120, 10)
            if chart_engine == CHART_LIVE:
                refresh = st.slider(
                    "Atualizar saldo/journal (seg)",
                    30,
                    300,
                    60,
                    15,
                    help="Saldo demo carrega automaticamente. Grafico ao vivo via WebSocket.",
                )
                auto = st.toggle("Auto-atualizar saldo/journal", value=True)
            else:
                refresh = st.slider("Atualizar pagina (seg)", 15, 300, 60, 15)
                auto = st.toggle("Auto-refresh", value=True)
        elif page == "ATLAS Intelligence":
            report_paths = discover_reports(PROJECT_ROOT / "data/reports")
            report_labels = [p.stem.replace("_report", "") for p in report_paths]
            selected_strategy = (
                st.selectbox("Estrategia (backtest)", report_labels) if report_labels else None
            )

        st.divider()
        st.subheader("Telegram")
        if alerts.enabled:
            st.success("Configurado")
            if st.button("Testar alerta", use_container_width=True):
                ok = alerts.send("ATLAS QUANT — teste de alerta OK")
                st.success("Enviado!" if ok else "Falhou")
        else:
            st.warning("Defina TELEGRAM_* no .env")

        if st.button("Atualizar pagina", use_container_width=True):
            st.rerun()

    if page == "Inicio":
        render_home(PROJECT_ROOT, load_config(PROJECT_ROOT / paper_config_rel))
    elif page == "Pesquisa":
        render_research(PROJECT_ROOT)
    elif page == "Paper Trading":
        render_paper(PROJECT_ROOT, paper_config_rel)
    elif page == "Historico Demo":
        render_trades_history(PROJECT_ROOT, paper_config_rel)
    elif page == "ATLAS Intelligence":
        report_paths = discover_reports(PROJECT_ROOT / "data/reports")
        if not report_paths or not selected_strategy:
            st.warning("Nenhum relatorio. Va em **Pesquisa** e rode um backtest.")
        else:
            sel_path = next(p for p in report_paths if p.stem.replace("_report", "") == selected_strategy)
            analysis = analyze_path(sel_path, market=config.exchange.symbol, timeframe=config.exchange.timeframe)
            render_intelligence(analysis)
    elif page == "Trading ao Vivo":
        _render_trading(config, service, paper_config_rel, refresh, bars, chart_engine, auto)


if __name__ == "__main__":
    main()
