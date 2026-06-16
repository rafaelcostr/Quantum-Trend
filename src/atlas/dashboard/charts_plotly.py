from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from atlas.dashboard.performance import PerformanceSnapshot, TradeMarker


CHART_COLORS = {
    "bg": "#0d1117",
    "grid": "#21262d",
    "up": "#26a69a",
    "down": "#ef5350",
    "mm20": "#58a6ff",
    "mm200": "#f0883e",
    "bb": "#8b949e",
    "rsi": "#a371f7",
    "adx": "#ffa657",
    "equity": "#58a6ff",
    "dd": "#f85149",
}


def build_price_chart(
    df: pd.DataFrame,
    markers: list[TradeMarker],
    bars: int = 120,
) -> go.Figure:
    view = df.tail(bars).copy()
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=("Preço + Indicadores", "Volume", "RSI", "ADX"),
    )

    fig.add_trace(
        go.Candlestick(
            x=view.index,
            open=view["open"],
            high=view["high"],
            low=view["low"],
            close=view["close"],
            name="BTC/USDT",
            increasing_line_color=CHART_COLORS["up"],
            decreasing_line_color=CHART_COLORS["down"],
        ),
        row=1,
        col=1,
    )

    for col, name, color, dash in [
        ("bb_upper", "BB Upper", CHART_COLORS["bb"], "dot"),
        ("bb_mid", "BB Mid", CHART_COLORS["bb"], "dash"),
        ("bb_lower", "BB Lower", CHART_COLORS["bb"], "dot"),
        ("mm20", "MM20", CHART_COLORS["mm20"], "solid"),
        ("mm200", "MM200", CHART_COLORS["mm200"], "solid"),
    ]:
        if col in view.columns:
            fig.add_trace(
                go.Scatter(
                    x=view.index,
                    y=view[col],
                    name=name,
                    line=dict(color=color, width=1.5, dash=dash),
                    opacity=0.85,
                ),
                row=1,
                col=1,
            )

    buys = [m for m in markers if m.side == "buy"]
    sells = [m for m in markers if m.side == "sell"]
    if buys:
        fig.add_trace(
            go.Scatter(
                x=[m.time for m in buys],
                y=[m.price for m in buys],
                mode="markers+text",
                name="Entrada",
                marker=dict(symbol="triangle-up", size=14, color="#3fb950"),
                text=[m.label[:16] for m in buys],
                textposition="bottom center",
            ),
            row=1,
            col=1,
        )
    if sells:
        fig.add_trace(
            go.Scatter(
                x=[m.time for m in sells],
                y=[m.price for m in sells],
                mode="markers+text",
                name="Saída",
                marker=dict(symbol="triangle-down", size=14, color="#f85149"),
                text=[m.label[:16] for m in sells],
                textposition="top center",
            ),
            row=1,
            col=1,
        )

    colors = [
        CHART_COLORS["up"] if c >= o else CHART_COLORS["down"]
        for o, c in zip(view["open"], view["close"], strict=True)
    ]
    fig.add_trace(
        go.Bar(x=view.index, y=view["volume"], name="Volume", marker_color=colors, opacity=0.7),
        row=2,
        col=1,
    )

    if "rsi" in view.columns:
        fig.add_trace(
            go.Scatter(x=view.index, y=view["rsi"], name="RSI", line=dict(color=CHART_COLORS["rsi"])),
            row=3,
            col=1,
        )
        fig.add_hline(y=70, line_dash="dot", line_color="#484f58", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#484f58", row=3, col=1)

    if "adx" in view.columns:
        fig.add_trace(
            go.Scatter(x=view.index, y=view["adx"], name="ADX", line=dict(color=CHART_COLORS["adx"])),
            row=4,
            col=1,
        )
        fig.add_hline(y=25, line_dash="dot", line_color="#484f58", row=4, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CHART_COLORS["bg"],
        plot_bgcolor=CHART_COLORS["bg"],
        height=820,
        margin=dict(l=40, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    for i in range(1, 5):
        fig.update_xaxes(gridcolor=CHART_COLORS["grid"], row=i, col=1)
        fig.update_yaxes(gridcolor=CHART_COLORS["grid"], row=i, col=1)
    return fig


def build_performance_charts(perf: PerformanceSnapshot) -> tuple[go.Figure, go.Figure]:
    if not perf.equity_curve:
        empty = go.Figure()
        empty.update_layout(
            template="plotly_dark",
            paper_bgcolor=CHART_COLORS["bg"],
            plot_bgcolor=CHART_COLORS["bg"],
            title="Sem dados de equity ainda — rode atlas trade paper",
        )
        return empty, empty

    curve = perf.equity_curve
    times = [p["ts"] for p in curve]
    equities = [p["equity"] for p in curve]
    peak = perf.initial_capital
    drawdowns = []
    for eq in equities:
        peak = max(peak, eq)
        drawdowns.append(-((peak - eq) / peak * 100) if peak > 0 else 0.0)

    equity_fig = go.Figure()
    equity_fig.add_trace(
        go.Scatter(
            x=times,
            y=equities,
            name="Equity",
            fill="tozeroy",
            line=dict(color=CHART_COLORS["equity"], width=2),
        )
    )
    equity_fig.add_hline(
        y=perf.initial_capital,
        line_dash="dash",
        line_color="#8b949e",
        annotation_text="Capital inicial",
    )
    equity_fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CHART_COLORS["bg"],
        plot_bgcolor=CHART_COLORS["bg"],
        height=280,
        margin=dict(l=40, r=20, t=30, b=20),
        title="Equity (USDT)",
        hovermode="x unified",
    )

    dd_fig = go.Figure()
    dd_fig.add_trace(
        go.Scatter(
            x=times,
            y=drawdowns,
            name="Drawdown %",
            fill="tozeroy",
            line=dict(color=CHART_COLORS["dd"], width=2),
        )
    )
    dd_fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CHART_COLORS["bg"],
        plot_bgcolor=CHART_COLORS["bg"],
        height=280,
        margin=dict(l=40, r=20, t=30, b=20),
        title="Drawdown %",
        yaxis_title="%",
        hovermode="x unified",
    )
    return equity_fig, dd_fig
