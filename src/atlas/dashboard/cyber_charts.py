"""Graficos cyberpunk — equity, barras, pizza 3D, drawdown."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go

from atlas.dashboard.theme import CYBER
from atlas.intelligence.metrics import discover_reports

PIE_COLORS = [
    CYBER["purple"],
    CYBER["cyan"],
    CYBER["magenta"],
    CYBER["green"],
    CYBER["yellow"],
    CYBER["pink"],
    CYBER["red"],
    "#6b5bff",
]


def apply_cyber_layout(fig: go.Figure, title: str, *, height: int = 320) -> go.Figure:
    fig.update_layout(
        title=dict(text=f"◈ {title}", font=dict(color=CYBER["cyan"], size=14, family="Orbitron")),
        paper_bgcolor=CYBER["bg"],
        plot_bgcolor=CYBER["panel"],
        font=dict(color=CYBER["text"], family="Share Tech Mono, Consolas, monospace", size=11),
        margin=dict(l=48, r=20, t=48, b=40),
        height=height,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=CYBER["text"])),
    )
    fig.update_xaxes(gridcolor=CYBER["grid"], zerolinecolor=CYBER["grid"])
    fig.update_yaxes(gridcolor=CYBER["grid"], zerolinecolor=CYBER["grid"])
    return fig


def build_equity_curve(perf, *, height: int = 340) -> go.Figure:
    fig = go.Figure()
    if perf and perf.equity_curve:
        times = [p["ts"] for p in perf.equity_curve]
        values = [p["equity"] for p in perf.equity_curve]
        fig.add_trace(
            go.Scatter(
                x=times,
                y=values,
                mode="lines",
                name="Equity",
                line=dict(color=CYBER["purple"], width=2.8),
                fill="tozeroy",
                fillcolor="rgba(189, 0, 255, 0.15)",
            )
        )
        fig.update_yaxes(tickprefix="$")
    else:
        fig.add_annotation(
            text="Sem curva — inicie o bot em Paper Trading",
            showarrow=False,
            font=dict(color=CYBER["muted"], size=13),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )
    return apply_cyber_layout(fig, "CURVA DE PATRIMÔNIO", height=height)


def build_drawdown_chart(perf, *, height: int = 260) -> go.Figure:
    fig = go.Figure()
    if perf and perf.equity_curve:
        peak = perf.initial_capital
        times, dds = [], []
        for p in perf.equity_curve:
            eq = float(p["equity"])
            peak = max(peak, eq)
            dd = (peak - eq) / peak if peak > 0 else 0.0
            times.append(p["ts"])
            dds.append(-dd * 100)
        fig.add_trace(
            go.Scatter(
                x=times,
                y=dds,
                mode="lines",
                fill="tozeroy",
                line=dict(color=CYBER["red"], width=2),
                fillcolor="rgba(255, 42, 109, 0.25)",
                name="Drawdown",
            )
        )
        fig.update_yaxes(ticksuffix="%")
    else:
        fig.add_annotation(
            text="Sem dados de drawdown",
            showarrow=False,
            font=dict(color=CYBER["muted"]),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )
    return apply_cyber_layout(fig, "ANÁLISE DE DRAWDOWN", height=height)


def _mesh_slice(theta0: float, theta1: float, r0: float, r1: float, z0: float, z1: float, n: int = 28):
    """Vertices e faces de um pedaco de anel 3D (fatia de pizza)."""
    if theta1 <= theta0:
        theta1 = theta0 + 0.01
    angles = np.linspace(theta0, theta1, n)
    x, y, z, i, j, k = [], [], [], [], [], []

    def ring(r, zlev):
        return [(r * np.cos(a), r * np.sin(a), zlev) for a in angles]

    inner_b, outer_b = ring(r0, z0), ring(r1, z0)
    inner_t, outer_t = ring(r0, z1), ring(r1, z1)
    verts = inner_b + outer_b + inner_t + outer_t
    x = [v[0] for v in verts]
    y = [v[1] for v in verts]
    z = [v[2] for v in verts]
    n_pts = len(angles)

    def idx(ring_i: int, pt: int) -> int:
        return ring_i * n_pts + pt

    for t in range(n_pts - 1):
        ib0, ib1 = idx(0, t), idx(0, t + 1)
        ob0, ob1 = idx(1, t), idx(1, t + 1)
        it0, it1 = idx(2, t), idx(2, t + 1)
        ot0, ot1 = idx(3, t), idx(3, t + 1)
        # topo
        i += [it0, it0]
        j += [ot0, ot1]
        k += [ot0, ot1]
        # base
        i += [ib0, ib0]
        j += [ob0, ob1]
        k += [ob1, ob0]
        # lateral externa
        i += [ob0, ob0]
        j += [ob1, ot1]
        k += [ot0, ot1]
        # lateral interna
        i += [ib0, ib0]
        j += [it0, it1]
        k += [ib1, it1]
        # radial inicio
        i += [ib0, ib0]
        j += [ob0, it0]
        k += [it0, ob0]
        # radial fim
        i += [ib1, ib1]
        j += [ob1, ot1]
        k += [it1, ob1]

    return x, y, z, i, j, k


def build_portfolio_pie_3d(allocations: dict[str, float], *, height: int = 380) -> go.Figure:
    """Pizza 3D cyberpunk — alocacao do portfolio."""
    labels, values = [], []
    for label, val in allocations.items():
        if val and val > 0:
            labels.append(label)
            values.append(float(val))
    fig = go.Figure()
    total = sum(values)
    if total <= 0:
        fig.add_annotation(
            text="Sem saldo para alocacao",
            showarrow=False,
            font=dict(color=CYBER["muted"]),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )
        fig.update_layout(
            paper_bgcolor=CYBER["bg"],
            plot_bgcolor=CYBER["bg"],
            height=height,
            scene=dict(bgcolor=CYBER["bg"]),
        )
        return apply_cyber_layout(fig, "ALOCAÇÃO 3D", height=height)

    cum = 0.0
    z0, z1 = 0.0, 0.35
    r0, r1 = 0.42, 1.0
    for idx, (label, val) in enumerate(zip(labels, values)):
        theta0 = 2 * np.pi * cum / total
        theta1 = 2 * np.pi * (cum + val) / total
        cum += val
        x, y, z, i, j, k = _mesh_slice(theta0, theta1, r0, r1, z0, z1)
        color = PIE_COLORS[idx % len(PIE_COLORS)]
        fig.add_trace(
            go.Mesh3d(
                x=x,
                y=y,
                z=z,
                i=i,
                j=j,
                k=k,
                color=color,
                opacity=0.92,
                name=label,
                hovertemplate=f"{label}<br>${val:,.0f}<extra></extra>",
                flatshading=True,
                lighting=dict(ambient=0.55, diffuse=0.85, specular=0.4, roughness=0.3),
            )
        )

    fig.update_layout(
        title=dict(
            text="◈ ALOCAÇÃO DE ATIVOS 3D",
            font=dict(color=CYBER["cyan"], size=14, family="Orbitron"),
        ),
        paper_bgcolor=CYBER["bg"],
        height=height,
        margin=dict(l=0, r=0, t=48, b=0),
        scene=dict(
            bgcolor=CYBER["bg"],
            xaxis=dict(visible=False, showgrid=False),
            yaxis=dict(visible=False, showgrid=False),
            zaxis=dict(visible=False, showgrid=False),
            aspectmode="data",
            camera=dict(eye=dict(x=1.6, y=1.6, z=0.9)),
        ),
        showlegend=True,
        legend=dict(
            bgcolor="rgba(13,13,31,0.9)",
            bordercolor=CYBER["border"],
            font=dict(color=CYBER["text"], size=10),
        ),
    )
    return fig


def build_strategy_returns_bar(project_root: Path, *, limit: int = 10, height: int = 340) -> go.Figure:
    """Barras — melhor retorno por backtest."""
    rows: list[tuple[str, float]] = []
    for path in discover_reports(project_root / "data/reports"):
        if path.name == "backtest_report.json":
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            meta = raw.get("metadata") or {}
            stats = raw.get("statistics") or {}
            ret = stats.get("net_profit_pct")
            if ret is None:
                continue
            strat = str(meta.get("strategy") or path.stem)
            tf = str(meta.get("timeframe") or "?").upper()
            quote = str(meta.get("quote") or "usdt").upper()
            label = f"{strat[:14]}\n{tf}/{quote}"
            rows.append((label, float(ret) * 100))
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            continue
    rows.sort(key=lambda r: r[1], reverse=True)
    rows = rows[:limit]
    fig = go.Figure()
    if not rows:
        fig.add_annotation(
            text="Rode backtests em Pesquisa",
            showarrow=False,
            font=dict(color=CYBER["muted"]),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )
        return apply_cyber_layout(fig, "RETORNO ESTRATÉGIAS", height=height)

    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    colors = [CYBER["green"] if v >= 0 else CYBER["red"] for v in values]
    fig.add_trace(
        go.Bar(
            x=labels,
            y=values,
            marker=dict(
                color=colors,
                line=dict(color=CYBER["cyan"], width=1),
            ),
            text=[f"{v:.1f}%" for v in values],
            textposition="outside",
            textfont=dict(color=CYBER["text"], size=10),
        )
    )
    fig.update_yaxes(ticksuffix="%", title="Retorno %")
    return apply_cyber_layout(fig, "RETORNO POR ESTRATÉGIA", height=height)


def build_exposure_bar(exposure_pct: float, in_market_pct: float, *, height: int = 220) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=["No mercado", "Em caixa"],
            y=[exposure_pct, max(0, 100 - exposure_pct)],
            marker=dict(
                color=[CYBER["magenta"], CYBER["cyan"]],
                line=dict(color=CYBER["purple"], width=1.5),
            ),
            text=[f"{exposure_pct:.0f}%", f"{100 - exposure_pct:.0f}%"],
            textposition="inside",
            textfont=dict(color="#fff", size=12),
        )
    )
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    return apply_cyber_layout(fig, f"EXPOSIÇÃO · {in_market_pct:.0f}% NO MERCADO", height=height)


def build_portfolio_summary_bars(allocations: dict[str, float], *, height: int = 300) -> go.Figure:
    labels = list(allocations.keys())
    values = [allocations[k] for k in labels]
    fig = go.Figure(
        go.Bar(
            y=labels,
            x=values,
            orientation="h",
            marker=dict(
                color=[PIE_COLORS[i % len(PIE_COLORS)] for i in range(len(labels))],
                line=dict(color=CYBER["cyan"], width=1),
            ),
            text=[f"${v:,.0f}" for v in values],
            textposition="outside",
            textfont=dict(color=CYBER["text"]),
        )
    )
    fig.update_xaxes(tickprefix="$")
    return apply_cyber_layout(fig, "COMPOSIÇÃO DO PORTFÓLIO", height=height)


def build_exposure_donut(exposure_pct: float, *, height: int = 260) -> go.Figure:
    """Rosca neon — % em mercado."""
    in_mkt = max(0, min(100, exposure_pct))
    cash = 100 - in_mkt
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["No mercado", "Caixa"],
                values=[in_mkt, cash],
                hole=0.62,
                marker=dict(
                    colors=[CYBER["magenta"], CYBER["cyan"]],
                    line=dict(color=CYBER["bg"], width=2),
                ),
                textinfo="none",
                hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title=dict(
            text=f"◈ EXPOSIÇÃO<br><span style='font-size:22px;color:{CYBER['green']}'>{in_mkt:.0f}%</span>",
            font=dict(color=CYBER["cyan"], size=13, family="Orbitron"),
            x=0.5,
        ),
        paper_bgcolor=CYBER["bg"],
        plot_bgcolor=CYBER["bg"],
        height=height,
        margin=dict(l=20, r=20, t=60, b=20),
        showlegend=True,
        legend=dict(font=dict(color=CYBER["text"], size=10)),
        annotations=[
            dict(
                text="EM MERCADO",
                x=0.5,
                y=0.48,
                font=dict(size=10, color=CYBER["muted"], family="Share Tech Mono"),
                showarrow=False,
            )
        ],
    )
    return fig


def build_risk_gauge(score: int, level: str, *, height: int = 280) -> go.Figure:
    color = CYBER["green"] if score < 35 else CYBER["yellow"] if score < 65 else CYBER["red"]
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number=dict(suffix="/100", font=dict(color=CYBER["text"], family="Orbitron")),
            title=dict(text="RISCO", font=dict(color=CYBER["cyan"], family="Orbitron", size=14)),
            gauge=dict(
                axis=dict(range=[0, 100], tickcolor=CYBER["muted"], dtick=20),
                bar=dict(color=color),
                bgcolor=CYBER["panel"],
                bordercolor=CYBER["purple"],
                borderwidth=2,
                steps=[
                    dict(range=[0, 35], color="rgba(57,255,20,0.15)"),
                    dict(range=[35, 65], color="rgba(252,238,10,0.12)"),
                    dict(range=[65, 100], color="rgba(255,42,109,0.15)"),
                ],
            ),
        )
    )
    fig.update_layout(
        paper_bgcolor=CYBER["bg"],
        height=height,
        margin=dict(l=30, r=30, t=50, b=10),
        font=dict(color=CYBER["text"]),
    )
    fig.add_annotation(
        text=f"NÍVEL: {level}",
        x=0.5,
        y=0.12,
        showarrow=False,
        font=dict(color=color, size=12, family="Share Tech Mono"),
    )
    return fig


def _mesh_box(cx: float, cy: float, w: float, h: float, d: float, color: str):
    """Caixa 3D centrada em (cx,cy), altura h em z."""
    x0, x1 = cx - w / 2, cx + w / 2
    y0, y1 = cy - d / 2, cy + d / 2
    z0, z1 = 0.0, max(0.05, h)
    verts = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [
        (0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),
        (1, 2, 6), (1, 6, 5), (0, 3, 7), (0, 7, 4),
    ]
    x = [v[0] for v in verts]
    y = [v[1] for v in verts]
    z = [v[2] for v in verts]
    i = [f[0] for f in faces]
    j = [f[1] for f in faces]
    k = [f[2] for f in faces]
    return x, y, z, i, j, k, color


def build_market_bars_3d(market_rows: list[dict], *, height: int = 320) -> go.Figure:
    """Barras 3D — variação dos ativos."""
    fig = go.Figure()
    if not market_rows:
        fig.add_annotation(text="Sem dados de mercado", showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)
        return apply_cyber_layout(fig, "MERCADO 24H (3D)", height=height)

    for i, row in enumerate(market_rows):
        chg = float(row.get("var_24h", 0)) * 100
        h = max(0.08, min(1.2, abs(chg) / 8))
        color = CYBER["green"] if chg >= 0 else CYBER["red"]
        x, y, z, ii, jj, kk, _ = _mesh_box(i * 1.4, 0, 0.9, h, 0.7, color)
        fig.add_trace(
            go.Mesh3d(
                x=x, y=y, z=z, i=ii, j=jj, k=kk,
                color=color,
                opacity=0.9,
                name=f"{row['ativo']} {chg:+.1f}%",
                hovertemplate=f"{row['ativo']}<br>{chg:+.2f}%<extra></extra>",
                flatshading=True,
            )
        )

    fig.update_layout(
        title=dict(text="◈ MERCADO · VARIAÇÃO %", font=dict(color=CYBER["cyan"], size=14, family="Orbitron")),
        paper_bgcolor=CYBER["bg"],
        height=height,
        margin=dict(l=0, r=0, t=48, b=0),
        scene=dict(
            bgcolor=CYBER["bg"],
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(title="%", tickfont=dict(color=CYBER["muted"]), gridcolor=CYBER["grid"]),
            camera=dict(eye=dict(x=1.8, y=-1.4, z=0.8)),
            aspectmode="manual",
            aspectratio=dict(x=2, y=1, z=1),
        ),
        showlegend=True,
        legend=dict(font=dict(color=CYBER["text"], size=9)),
    )
    return fig


def build_sparkline_figure(spark: list[float], *, color: str | None = None) -> go.Figure:
    c = color or CYBER["purple"]
    fig = go.Figure(go.Scatter(x=list(range(len(spark))), y=spark, mode="lines", line=dict(color=c, width=1.5)))
    fig.update_layout(
        margin=dict(l=4, r=4, t=4, b=4),
        height=50,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig
