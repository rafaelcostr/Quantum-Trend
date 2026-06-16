"""Dashboard — painel inicial completo (estilo mockup cyberpunk, PT-BR)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from atlas.core.config import AtlasConfig
from atlas.dashboard.actions import run_export_all_reports
from atlas.dashboard.bot_manager import bot_status, start_bot, stop_bot
from atlas.dashboard.cyber_charts import (
    build_drawdown_chart,
    build_equity_curve,
    build_exposure_donut,
    build_market_bars_3d,
    build_portfolio_pie_3d,
    build_portfolio_summary_bars,
    build_risk_gauge,
    build_sparkline_figure,
)
from atlas.dashboard.home_data import (
    compute_daily_pnl,
    compute_risk_score,
    fetch_market_overview,
    journal_feed,
    live_snapshot,
    load_backtest_stats,
    load_recent_trades,
    load_signal_monitor_rows,
    performance_metrics_rows,
    portfolio_allocations,
    system_logs,
)
from atlas.dashboard.strategy_config import save_active_config
from atlas.dashboard.theme import (
    CYBER,
    cyber_banner_info,
    cyber_banner_ok,
    cyber_events,
    cyber_hero,
    cyber_kpi_row,
    cyber_panel,
    cyber_risk_panel,
    cyber_section_title,
    cyber_status_bar,
    format_uptime,
)
from atlas.intelligence.metrics import discover_reports
from atlas.monitoring.alerts import TelegramAlerts
from atlas.strategies.metadata import get_strategy_metadata


def _pct(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val:.2%}"


def _num(val: float | None, *, prefix: str = "", decimals: int = 2) -> str:
    if val is None:
        return "N/A"
    return f"{prefix}{val:,.{decimals}f}"


def render_home(project_root: Path, config: AtlasConfig) -> None:
    status = bot_status()
    alerts = TelegramAlerts()
    reports = discover_reports(project_root / "data/reports")
    meta = get_strategy_metadata(config.strategy.name)
    bt_stats = load_backtest_stats(project_root, config)
    now_local = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    st.markdown(cyber_hero(), unsafe_allow_html=True)

    bot_cls = "ok" if status.get("running") else "warn"
    st.markdown(
        cyber_status_bar(
            [
                ("Mercado", config.exchange.symbol, ""),
                ("Tempo Grafico", config.exchange.timeframe.upper(), ""),
                ("Status Bot", "EM EXECUCAO" if status.get("running") else "PARADO", bot_cls),
                ("Tempo Ativo", format_uptime(status.get("started_at")), ""),
                ("Conta", "BINANCE DEMO", ""),
                ("Relatorios", str(len(reports)), ""),
                ("Hora", now_local, ""),
                ("Telegram", "ON" if alerts.enabled else "OFF", "ok" if alerts.enabled else "err"),
            ]
        ),
        unsafe_allow_html=True,
    )

    balance_error: str | None = None
    balances = None
    state = None
    perf = None
    events = []
    try:
        state, perf, events, balance_error, balances = live_snapshot(project_root, config)
    except Exception:
        pass

    btc_price = state.last_close if state else 0.0
    alloc = portfolio_allocations(balances, state, btc_price)
    total_alloc = sum(alloc.values())
    exposure_pct = (alloc.get("BTC", 0) / total_alloc * 100) if total_alloc > 0 else 0.0

    daily_pnl, daily_pnl_pct = compute_daily_pnl(events, config.risk.initial_capital)
    risk_score, risk_level = compute_risk_score(
        config, perf, exposure_pct, perf.max_drawdown_pct if perf else 0.0
    )

    equity_txt = _num(state.equity_usdt, prefix="$") if state and not balance_error else "N/A"
    pnl_txt = _num(perf.net_pnl, prefix="$") if perf and not balance_error else "N/A"
    pnl_delta = _pct(perf.net_pnl_pct) if perf and not balance_error else ""
    dd_txt = _pct(perf.max_drawdown_pct) if perf and not balance_error else "N/A"
    pnl_color = CYBER["green"] if perf and perf.net_pnl >= 0 else CYBER["red"]
    daily_color = CYBER["green"] if daily_pnl >= 0 else CYBER["red"]

    win_rate = _pct(bt_stats.get("win_rate")) if bt_stats else "N/A"
    pf = _num(bt_stats.get("profit_factor"), decimals=2) if bt_stats else "N/A"
    sharpe = _num(bt_stats.get("sharpe_ratio"), decimals=2) if bt_stats else "N/A"

    st.markdown(
        cyber_kpi_row(
            [
                ("Patrimonio", equity_txt, pnl_delta if equity_txt != "N/A" else "", CYBER["cyan"]),
                ("PnL Diario", _num(daily_pnl, prefix="$"), _pct(daily_pnl_pct), daily_color),
                ("PnL Total", pnl_txt, pnl_delta, pnl_color),
                ("Taxa Vitoria", win_rate, "backtest", CYBER["text"]),
                ("Fator Lucro", pf, "backtest", CYBER["text"]),
                ("Indice Sharpe", sharpe, "backtest", CYBER["text"]),
                ("Rebaixamento", dd_txt, "max", CYBER["red"]),
            ]
        ),
        unsafe_allow_html=True,
    )

    # --- Linha principal: curva + estrategia + noticias ---
    m1, m2, m3 = st.columns([2.2, 1, 1])
    with m1:
        if perf:
            st.plotly_chart(build_equity_curve(perf, height=380), use_container_width=True)
    with m2:
        pos_size = f"{config.risk.risk_per_trade:.2%} por trade"
        strat_rows = [
            ("Estrategia", config.strategy.name.upper()),
            ("Versao", f"v{meta.get('version', '1.0.0')}"),
            ("Tipo", meta.get("type", "N/A")),
            ("Tempo Grafico", config.exchange.timeframe.upper()),
            ("Modelo Risco", getattr(config.risk, "sizing_mode", "risk_based")),
            ("Tamanho Posicao", pos_size),
            ("Status", "ATIVA" if status.get("running") else "INATIVA"),
        ]
        if state and not balance_error:
            strat_rows.extend(
                [
                    ("Preco BTC", f"${state.last_close:,.2f}"),
                    ("Sinal", state.signal.replace("_", " ").upper()),
                    ("Posicao", "LONG BTC" if state.in_position else "FLAT"),
                ]
            )
        st.markdown(cyber_panel("Estrategia Ativa", strat_rows, accent=CYBER["magenta"]), unsafe_allow_html=True)
    with m3:
        st.markdown(
            cyber_events("Noticias e Eventos", journal_feed(events)),
            unsafe_allow_html=True,
        )

    # --- Portfolio ---
    st.markdown(cyber_section_title("PORTFOLIO E ALOCACAO"), unsafe_allow_html=True)
    p1, p2, p3 = st.columns(3)
    with p1:
        st.plotly_chart(build_portfolio_pie_3d(alloc, height=340), use_container_width=True)
    with p2:
        if alloc:
            st.plotly_chart(build_portfolio_summary_bars(alloc, height=340), use_container_width=True)
        else:
            st.markdown(cyber_panel("Portfolio", [("Status", "Configure API demo")]), unsafe_allow_html=True)
    with p3:
        st.plotly_chart(build_exposure_donut(exposure_pct, height=340), use_container_width=True)

    # --- Analytics: metricas + drawdown + risco ---
    st.markdown(cyber_section_title("ANALISE DE PERFORMANCE E RISCO"), unsafe_allow_html=True)
    a1, a2, a3 = st.columns([1, 1.2, 1])
    with a1:
        perf_rows = performance_metrics_rows(bt_stats, perf, config)
        st.markdown(cyber_panel("Metricas de Desempenho", perf_rows), unsafe_allow_html=True)
    with a2:
        if perf:
            st.plotly_chart(build_drawdown_chart(perf, height=320), use_container_width=True)
    with a3:
        st.plotly_chart(build_risk_gauge(risk_score, risk_level, height=200), use_container_width=True)
        st.markdown(
            cyber_risk_panel(
                risk_score,
                risk_level,
                [
                    ("Limite Perda Diaria", f"{config.risk.max_daily_drawdown:.2%}"),
                    ("Drawdown Maximo", f"{config.risk.max_weekly_drawdown:.2%}"),
                    ("Exposicao Atual", f"{exposure_pct:.1f}%"),
                    ("Risco por Trade", f"{config.risk.risk_per_trade:.2%}"),
                ],
            ),
            unsafe_allow_html=True,
        )

    # --- Mercado + sinais + trades ---
    st.markdown(cyber_section_title("MERCADO, SINAIS E OPERACOES"), unsafe_allow_html=True)
    market_rows = fetch_market_overview(config.exchange.timeframe)

    b1, b2, b3 = st.columns([1.2, 1, 1])
    with b1:
        st.plotly_chart(build_market_bars_3d(market_rows, height=300), use_container_width=True)
        if market_rows:
            st.markdown("**Visao Geral do Mercado**")
            mdf = pd.DataFrame(
                [
                    {
                        "Ativo": r["ativo"],
                        "Preco": f"${r['preco']:,.2f}",
                        "Var %": f"{r['var_24h']:+.2%}",
                    }
                    for r in market_rows
                ]
            )
            st.dataframe(mdf, use_container_width=True, hide_index=True)
            spark_cols = st.columns(min(len(market_rows), 5))
            for i, row in enumerate(market_rows[:5]):
                with spark_cols[i]:
                    color = CYBER["green"] if row["var_24h"] >= 0 else CYBER["red"]
                    st.caption(row["ativo"])
                    st.plotly_chart(
                        build_sparkline_figure(row["spark"], color=color),
                        use_container_width=True,
                        config={"displayModeBar": False},
                    )
    with b2:
        st.markdown("**Monitor de Sinais**")
        signals = load_signal_monitor_rows(project_root)
        if signals:
            sdf = pd.DataFrame(signals)
            sdf = sdf.rename(
                columns={
                    "par": "Par",
                    "estrategia": "Estrategia",
                    "tf": "TF",
                    "sinal": "Sinal",
                    "forca": "Forca %",
                }
            )
            st.dataframe(sdf, use_container_width=True, hide_index=True)
        else:
            st.info("Rode backtests em Pesquisa para ver sinais.")

    with b3:
        st.markdown("**Operacoes Recentes**")
        trades = load_recent_trades(project_root, config)
        if trades:
            tdf = pd.DataFrame(trades)
            tdf = tdf.rename(columns={"hora": "Hora", "lado": "Lado", "par": "Par", "pnl": "Valor"})
            st.dataframe(tdf, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum trade na conta demo ainda.")

    # --- Acoes rapidas + logs ---
    st.markdown(cyber_section_title("ACOES RAPIDAS E LOGS"), unsafe_allow_html=True)
    q1, q2, q3, q4 = st.columns(4)
    with q1:
        if st.button("INICIAR BOT", type="primary", use_container_width=True, disabled=status.get("running")):
            active_rel = save_active_config(project_root, config)
            res = start_bot(project_root, active_rel)
            st.success(res["message"]) if res.get("ok") else st.warning(res["message"])
            st.rerun()
    with q2:
        if st.button("PARAR BOT", use_container_width=True, disabled=not status.get("running")):
            res = stop_bot()
            st.success(res["message"])
            st.rerun()
    with q3:
        if st.button("GERAR RELATORIO", use_container_width=True):
            with st.spinner("Exportando..."):
                st.session_state["export_result"] = run_export_all_reports(project_root)
            st.success("Relatorio gerado! Va em Pesquisa → Comparar para baixar.")
    with q4:
        st.caption("Backtest em lote: sidebar → **Pesquisa**")

    log_col1, log_col2 = st.columns([1, 1])
    with log_col1:
        st.markdown("**Logs do Sistema**")
        st.code(system_logs(14), language="text")
    with log_col2:
        if balance_error:
            st.markdown(
                cyber_banner_info(f"API demo: {balance_error}"),
                unsafe_allow_html=True,
            )
        if status.get("running"):
            st.markdown(
                cyber_banner_ok(
                    f"Bot em execucao (PID {status.get('pid')}) · "
                    f"Uptime {format_uptime(status.get('started_at'))}"
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                cyber_banner_info("Bot parado. Clique em INICIAR BOT ou va em Paper Trading."),
                unsafe_allow_html=True,
            )

    st.caption(
        f"ATLAS QUANT v2.1 · {config.strategy.name} · "
        f"{config.exchange.symbol} {config.exchange.timeframe}"
    )
