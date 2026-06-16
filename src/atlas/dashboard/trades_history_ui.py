"""Historico de trades da conta demo — visual cyberpunk."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from atlas.core.config import AtlasConfig
from atlas.dashboard.cyber_charts import apply_cyber_layout
from atlas.dashboard.service import DashboardService
from atlas.dashboard.theme import CYBER, cyber_page_header


def _cyber_layout(fig: go.Figure, title: str) -> go.Figure:
    return apply_cyber_layout(fig, title.replace("◈ ", ""))


def trades_to_dataframe(trades: list[dict[str, Any]]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    rows = []
    for t in trades:
        ts = t.get("timestamp")
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=timezone.utc)
        elif ts:
            dt = pd.Timestamp(ts).to_pydatetime()
        else:
            dt = datetime.now(timezone.utc)
        side = str(t.get("side", "")).lower()
        rows.append(
            {
                "time": dt,
                "side": side,
                "price": float(t.get("price") or 0),
                "amount": float(t.get("amount") or 0),
                "cost": float(t.get("cost") or 0),
                "fee": float(t.get("fee") or 0),
                "symbol": t.get("symbol", ""),
                "id": t.get("id", ""),
            }
        )
    df = pd.DataFrame(rows).sort_values("time")
    if df.empty:
        return df
    signed = df.apply(lambda r: r["cost"] if r["side"] == "buy" else -r["cost"], axis=1)
    df["signed_flow"] = signed
    df["cum_flow"] = signed.cumsum()
    return df


def build_cyberpunk_trade_charts(df: pd.DataFrame) -> tuple[go.Figure, go.Figure, go.Figure]:
    if df.empty:
        empty = go.Figure()
        empty.update_layout(
            paper_bgcolor=CYBER["bg"],
            plot_bgcolor=CYBER["panel"],
            annotations=[dict(text="Sem trades na conta demo", showarrow=False, font=dict(color=CYBER["text"]))],
        )
        return empty, empty, empty

    buys = df[df["side"] == "buy"]
    sells = df[df["side"] == "sell"]

    # Timeline de execucoes
    fig_tl = go.Figure()
    if not buys.empty:
        fig_tl.add_trace(
            go.Scatter(
                x=buys["time"],
                y=buys["price"],
                mode="markers",
                name="COMPRA",
                marker=dict(symbol="triangle-up", size=14, color=CYBER["green"], line=dict(width=1, color=CYBER["cyan"])),
            )
        )
    if not sells.empty:
        fig_tl.add_trace(
            go.Scatter(
                x=sells["time"],
                y=sells["price"],
                mode="markers",
                name="VENDA",
                marker=dict(symbol="triangle-down", size=14, color=CYBER["red"], line=dict(width=1, color=CYBER["magenta"])),
            )
        )
    fig_tl.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["price"],
            mode="lines",
            name="Preco",
            line=dict(color=CYBER["purple"], width=1, dash="dot"),
            opacity=0.5,
        )
    )
    _cyber_layout(fig_tl, "◈ EXECUCOES DEMO — TIMELINE")

    # Volume por trade
    colors = [CYBER["green"] if s == "buy" else CYBER["red"] for s in df["side"]]
    fig_vol = go.Figure(
        go.Bar(
            x=df["time"],
            y=df["cost"],
            marker_color=colors,
            marker_line=dict(color=CYBER["cyan"], width=0.5),
            name="Volume",
        )
    )
    _cyber_layout(fig_vol, "◈ VOLUME POR TRADE")

    # Fluxo acumulado (compras - vendas em quote)
    fig_flow = go.Figure()
    fig_flow.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["cum_flow"],
            mode="lines+markers",
            fill="tozeroy",
            fillcolor="rgba(0, 240, 255, 0.08)",
            line=dict(color=CYBER["cyan"], width=2),
            marker=dict(size=6, color=CYBER["yellow"]),
            name="Fluxo acumulado",
        )
    )
    _cyber_layout(fig_flow, "◈ FLUXO ACUMULADO (QUOTE)")

    return fig_tl, fig_vol, fig_flow


def build_cyberpunk_pnl_heatmap(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        _cyber_layout(fig, "◈ HEATMAP HORARIO")
        return fig

    tmp = df.copy()
    tmp["dow"] = tmp["time"].dt.day_name()
    tmp["hour"] = tmp["time"].dt.hour
    pivot = tmp.pivot_table(index="dow", columns="hour", values="cost", aggfunc="sum", fill_value=0)
    if pivot.empty:
        fig = go.Figure()
        _cyber_layout(fig, "◈ HEATMAP HORARIO")
        return fig
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = pivot.reindex([d for d in order if d in pivot.index])

    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=[f"{h:02d}h" for h in pivot.columns],
            y=list(pivot.index),
            colorscale=[
                [0, CYBER["bg"]],
                [0.3, CYBER["purple"]],
                [0.6, CYBER["magenta"]],
                [1, CYBER["cyan"]],
            ],
            colorbar=dict(title="Volume", titlefont=dict(color=CYBER["text"])),
        )
    )
    _cyber_layout(fig, "◈ HEATMAP — DIA x HORA")
    return fig


def render_trades_history(project_root: Path, paper_config_rel: str = "config/paper.yaml") -> None:
    from atlas.dashboard.ops_context import get_ops_config

    config = get_ops_config(project_root, paper_config_rel)
    st.markdown(
        cyber_page_header(
            "HISTORICO DEMO",
            f"{config.exchange.symbol} {config.exchange.timeframe} · {config.strategy.name}",
        ),
        unsafe_allow_html=True,
    )

    service = DashboardService(config)
    limit = st.slider("Max trades", 50, 1000, 300, 50, key="hist_limit")

    try:
        with st.spinner("Sincronizando trades da Binance Demo..."):
            trades, err = service.fetch_demo_trades(limit=limit)
    except Exception as exc:
        st.error(f"Erro ao carregar historico: {exc}")
        st.info("Verifique BINANCE_DEMO_API_KEY/SECRET no .env e reinicie o dashboard.")
        return

    if err:
        st.warning(err)

    df = trades_to_dataframe(trades)

    if df.empty:
        st.info("Nenhum trade encontrado nesta conta demo. Inicie o bot em **Paper Trading**.")
        return

    buys = int((df["side"] == "buy").sum())
    sells = int((df["side"] == "sell").sum())
    total_vol = float(df["cost"].sum())
    total_fee = float(df["fee"].sum())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Trades", len(df))
    c2.metric("Compras", buys)
    c3.metric("Vendas", sells)
    c4.metric("Volume total", f"${total_vol:,.2f}")
    c5.metric("Taxas", f"${total_fee:,.4f}")

    fig_tl, fig_vol, fig_flow = build_cyberpunk_trade_charts(df)
    st.plotly_chart(fig_tl, use_container_width=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(fig_vol, use_container_width=True)
    with col_b:
        st.plotly_chart(fig_flow, use_container_width=True)
    st.plotly_chart(build_cyberpunk_pnl_heatmap(df), use_container_width=True)

    st.markdown(f"### ◈ Registro completo")
    display = df.copy()
    display["time"] = display["time"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    display = display.rename(
        columns={
            "time": "Hora",
            "side": "Lado",
            "price": "Preco",
            "amount": "BTC",
            "cost": "Valor",
            "fee": "Taxa",
            "symbol": "Par",
            "id": "ID",
        }
    )
    st.dataframe(display[["Hora", "Lado", "Par", "Preco", "BTC", "Valor", "Taxa", "ID"]], use_container_width=True, hide_index=True)
