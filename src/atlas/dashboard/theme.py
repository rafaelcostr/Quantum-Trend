"""Tema cyberpunk ATLAS QUANT — cores, CSS e componentes HTML."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

CYBER = {
    "bg": "#050510",
    "panel": "#0d0d1f",
    "panel2": "#12122a",
    "border": "#2a1a4a",
    "cyan": "#00f0ff",
    "magenta": "#ff00aa",
    "pink": "#ff2a9a",
    "yellow": "#fcee0a",
    "green": "#39ff14",
    "red": "#ff2a6d",
    "purple": "#bd00ff",
    "text": "#c8d6e5",
    "muted": "#7a8a9e",
    "grid": "rgba(0, 240, 255, 0.12)",
    "glow": "rgba(189, 0, 255, 0.35)",
}


def inject_cyber_css() -> str:
    c = CYBER
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&family=Share+Tech+Mono&display=swap');

.stApp {{
    background: radial-gradient(ellipse at 20% 0%, rgba(189,0,255,0.12) 0%, transparent 45%),
                radial-gradient(ellipse at 80% 100%, rgba(0,240,255,0.08) 0%, transparent 40%),
                {c["bg"]};
}}
.block-container {{
    padding-top: 1.2rem;
    max-width: 1400px;
}}
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {c["panel2"]} 0%, {c["bg"]} 100%);
    border-right: 1px solid {c["border"]};
}}
[data-testid="stSidebar"] [data-testid="stMarkdown"] h1 {{
    font-family: 'Orbitron', sans-serif;
    color: {c["cyan"]};
    text-shadow: 0 0 12px {c["glow"]};
    letter-spacing: 0.08em;
}}
[data-testid="stMetric"] {{
    background: {c["panel"]};
    border: 1px solid {c["border"]};
    border-radius: 10px;
    padding: 10px 14px;
    box-shadow: 0 0 18px rgba(0,240,255,0.06);
}}
[data-testid="stMetric"] label {{
    color: {c["muted"]} !important;
    font-family: 'Share Tech Mono', Consolas, monospace;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    color: {c["text"]} !important;
    font-family: 'Share Tech Mono', Consolas, monospace;
}}
.atlas-hero {{
    background: linear-gradient(135deg, rgba(13,13,31,0.95) 0%, rgba(42,26,74,0.55) 100%);
    border: 1px solid {c["purple"]};
    border-radius: 14px;
    padding: 22px 28px;
    margin-bottom: 18px;
    box-shadow: 0 0 28px {c["glow"]};
}}
.atlas-hero h1 {{
    margin: 0;
    font-family: 'Orbitron', sans-serif;
    font-size: 1.85rem;
    color: {c["cyan"]};
    letter-spacing: 0.12em;
    text-shadow: 0 0 20px rgba(0,240,255,0.45);
}}
.atlas-hero p {{
    margin: 6px 0 0;
    color: {c["muted"]};
    font-family: 'Share Tech Mono', Consolas, monospace;
    font-size: 0.85rem;
}}
.atlas-status-bar {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 16px;
}}
.atlas-pill {{
    background: {c["panel"]};
    border: 1px solid {c["border"]};
    border-radius: 8px;
    padding: 6px 12px;
    font-family: 'Share Tech Mono', Consolas, monospace;
    font-size: 0.78rem;
    color: {c["text"]};
}}
.atlas-pill b {{ color: {c["cyan"]}; }}
.atlas-pill.ok {{ border-color: {c["green"]}; color: {c["green"]}; }}
.atlas-pill.warn {{ border-color: {c["yellow"]}; }}
.atlas-pill.err {{ border-color: {c["red"]}; }}
.atlas-kpi-row {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 12px;
    margin-bottom: 18px;
}}
.atlas-kpi {{
    background: linear-gradient(160deg, {c["panel"]} 0%, {c["panel2"]} 100%);
    border: 1px solid {c["border"]};
    border-radius: 12px;
    padding: 14px 16px;
    box-shadow: inset 0 0 20px rgba(0,0,0,0.25);
}}
.atlas-kpi:hover {{
    border-color: {c["purple"]};
    box-shadow: 0 0 16px {c["glow"]};
}}
.atlas-kpi-label {{
    font-family: 'Share Tech Mono', Consolas, monospace;
    font-size: 0.68rem;
    color: {c["muted"]};
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
}}
.atlas-kpi-value {{
    font-family: 'Orbitron', sans-serif;
    font-size: 1.25rem;
    color: {c["text"]};
    line-height: 1.2;
}}
.atlas-kpi-delta {{
    font-family: 'Share Tech Mono', Consolas, monospace;
    font-size: 0.75rem;
    margin-top: 4px;
}}
.atlas-panel {{
    background: {c["panel"]};
    border: 1px solid {c["border"]};
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 12px;
    height: 100%;
}}
.atlas-panel-title {{
    font-family: 'Orbitron', sans-serif;
    font-size: 0.82rem;
    color: {c["cyan"]};
    letter-spacing: 0.1em;
    margin: 0 0 12px;
    text-transform: uppercase;
}}
.atlas-panel-title::before {{ content: "◈ "; color: {c["magenta"]}; }}
.atlas-row-label {{
    display: flex;
    justify-content: space-between;
    font-family: 'Share Tech Mono', Consolas, monospace;
    font-size: 0.78rem;
    color: {c["muted"]};
    padding: 5px 0;
    border-bottom: 1px solid rgba(42,26,74,0.6);
}}
.atlas-row-label span:last-child {{ color: {c["text"]}; }}
.atlas-event {{
    font-family: 'Share Tech Mono', Consolas, monospace;
    font-size: 0.72rem;
    padding: 8px 0;
    border-bottom: 1px solid rgba(42,26,74,0.5);
    color: {c["muted"]};
}}
.atlas-event b {{ color: {c["cyan"]}; }}
.atlas-workflow {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin: 16px 0;
}}
.atlas-step {{
    background: {c["panel"]};
    border: 1px solid {c["border"]};
    border-radius: 10px;
    padding: 14px;
    transition: border-color 0.2s;
}}
.atlas-step:hover {{ border-color: {c["purple"]}; }}
.atlas-step-num {{
    font-family: 'Orbitron', sans-serif;
    color: {c["magenta"]};
    font-size: 0.75rem;
}}
.atlas-step-title {{
    font-family: 'Orbitron', sans-serif;
    color: {c["text"]};
    font-size: 0.9rem;
    margin: 6px 0 4px;
}}
.atlas-step-desc {{
    font-family: 'Share Tech Mono', Consolas, monospace;
    font-size: 0.72rem;
    color: {c["muted"]};
    line-height: 1.4;
}}
.atlas-banner-ok {{
    background: rgba(57,255,20,0.08);
    border: 1px solid {c["green"]};
    border-radius: 10px;
    padding: 12px 16px;
    color: {c["green"]};
    font-family: 'Share Tech Mono', Consolas, monospace;
    font-size: 0.82rem;
    margin: 12px 0;
}}
.atlas-banner-info {{
    background: rgba(0,240,255,0.06);
    border: 1px solid {c["cyan"]};
    border-radius: 10px;
    padding: 12px 16px;
    color: {c["cyan"]};
    font-family: 'Share Tech Mono', Consolas, monospace;
    font-size: 0.82rem;
    margin: 12px 0;
}}
.stTabs [data-baseweb="tab-list"] {{
    gap: 8px;
}}
.stTabs [data-baseweb="tab"] {{
    background: {c["panel"]};
    border: 1px solid {c["border"]};
    border-radius: 8px;
    color: {c["muted"]};
    font-family: 'Share Tech Mono', Consolas, monospace;
    font-size: 0.78rem;
}}
.stTabs [aria-selected="true"] {{
    background: {c["panel2"]} !important;
    border-color: {c["purple"]} !important;
    color: {c["cyan"]} !important;
}}
[data-testid="stDataFrame"] {{
    border: 1px solid {c["border"]};
    border-radius: 10px;
}}
</style>
"""


def _esc(text: Any) -> str:
    return html.escape(str(text))


def cyber_hero(title: str = "ATLAS QUANT", subtitle: str = "Bot de Trading Quantitativo") -> str:
    return f"""
<div class="atlas-hero">
  <h1>◈ {_esc(title)}</h1>
  <p>{_esc(subtitle)} · Centro de controle — pesquisa, paper trading e monitoramento</p>
</div>
"""


def cyber_pill(label: str, value: str, *, style: str = "") -> str:
    cls = f"atlas-pill {style}".strip()
    return f'<span class="{cls}">{_esc(label)}: <b>{_esc(value)}</b></span>'


def cyber_status_bar(pills: list[tuple[str, str, str]]) -> str:
    """pills: [(label, value, style_class), ...]"""
    inner = "".join(cyber_pill(l, v, style=s) for l, v, s in pills)
    return f'<div class="atlas-status-bar">{inner}</div>'


def cyber_kpi(label: str, value: str, delta: str = "", *, color: str | None = None) -> str:
    delta_html = ""
    if delta:
        delta_color = color or CYBER["muted"]
        delta_html = f'<div class="atlas-kpi-delta" style="color:{delta_color}">{_esc(delta)}</div>'
    value_color = f' style="color:{color}"' if color else ""
    return f"""
<div class="atlas-kpi">
  <div class="atlas-kpi-label">{_esc(label)}</div>
  <div class="atlas-kpi-value"{value_color}>{_esc(value)}</div>
  {delta_html}
</div>
"""


def cyber_kpi_row(items: list[tuple[str, str, str, str | None]]) -> str:
    """(label, value, delta, color)"""
    cards = "".join(cyber_kpi(l, v, d, color=c) for l, v, d, c in items)
    return f'<div class="atlas-kpi-row">{cards}</div>'


def cyber_panel(title: str, rows: list[tuple[str, str]], *, accent: str | None = None) -> str:
    row_html = "".join(
        f'<div class="atlas-row-label"><span>{_esc(k)}</span><span>{_esc(v)}</span></div>'
        for k, v in rows
    )
    title_style = f' style="color:{accent}"' if accent else ""
    return f"""
<div class="atlas-panel">
  <div class="atlas-panel-title"{title_style}>{_esc(title)}</div>
  {row_html}
</div>
"""


def cyber_events(title: str, events: list[tuple[str, str, str]]) -> str:
    """(time, event, detail)"""
    if not events:
        body = f'<div class="atlas-event">Sem eventos recentes.</div>'
    else:
        body = "".join(
            f'<div class="atlas-event"><b>{_esc(t)}</b> · {_esc(ev)}<br>{_esc(det)}</div>'
            for t, ev, det in events
        )
    return f"""
<div class="atlas-panel">
  <div class="atlas-panel-title">{_esc(title)}</div>
  {body}
</div>
"""


def cyber_workflow(steps: list[tuple[str, str, str, str]]) -> str:
    """(num, title, desc, page)"""
    cards = "".join(
        f"""
<div class="atlas-step">
  <div class="atlas-step-num">{_esc(num)}</div>
  <div class="atlas-step-title">{_esc(title)}</div>
  <div class="atlas-step-desc">{_esc(desc)} → sidebar: <b>{_esc(page)}</b></div>
</div>
"""
        for num, title, desc, page in steps
    )
    return f'<div class="atlas-workflow">{cards}</div>'


def cyber_banner_ok(text: str) -> str:
    return f'<div class="atlas-banner-ok">{_esc(text)}</div>'


def cyber_banner_info(text: str) -> str:
    return f'<div class="atlas-banner-info">{_esc(text)}</div>'


def format_uptime(started_at: str | None) -> str:
    if not started_at:
        return "—"
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - start
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        mins, secs = divmod(rem, 60)
        if days:
            return f"{days}D {hours:02d}:{mins:02d}:{secs:02d}"
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    except ValueError:
        return "—"


def cyber_page_header(title: str, subtitle: str = "") -> str:
    sub = f"<p>{_esc(subtitle)}</p>" if subtitle else ""
    return f'<div class="atlas-hero"><h1>◈ {_esc(title)}</h1>{sub}</div>'


def cyber_section_title(title: str) -> str:
    return f'<div class="atlas-panel-title" style="margin:20px 0 12px;font-size:0.95rem;">{_esc(title)}</div>'


def cyber_metric_card(label: str, value: str, status: str, emoji: str = "") -> str:
    return f"""
<div style="background:{CYBER['panel']};border:1px solid {CYBER['border']};border-radius:10px;
padding:12px;margin-bottom:8px;box-shadow:0 0 12px rgba(189,0,255,0.08);">
  <div style="color:{CYBER['muted']};font-size:11px;font-family:'Share Tech Mono',monospace;
  text-transform:uppercase;letter-spacing:0.06em;">{_esc(label)}</div>
  <div style="font-size:22px;font-weight:600;color:{CYBER['text']};font-family:Orbitron,sans-serif;">
    {_esc(value)}</div>
  <div style="font-size:12px;color:{CYBER['cyan']};">{_esc(emoji)} {_esc(status)}</div>
</div>
"""


def cyber_risk_panel(score: int, level: str, limits: list[tuple[str, str]]) -> str:
    color = CYBER["green"] if score < 35 else CYBER["yellow"] if score < 65 else CYBER["red"]
    rows = "".join(
        f'<div class="atlas-row-label"><span>{_esc(k)}</span><span>{_esc(v)}</span></div>'
        for k, v in limits
    )
    return f"""
<div class="atlas-panel">
  <div class="atlas-panel-title">GESTOR DE RISCO</div>
  <div style="text-align:center;margin:8px 0;">
    <span style="font-family:Orbitron;font-size:2rem;color:{color};">{score}</span>
    <span style="color:{CYBER['muted']};">/100</span>
    <div style="color:{color};font-family:'Share Tech Mono',monospace;font-size:0.8rem;">
      NÍVEL {level}
    </div>
  </div>
  {rows}
</div>
"""


def cyber_indicator_pills(items: list[tuple[str, str, str | None]]) -> str:
    """(label, value, color_optional)"""
    pills = []
    for label, value, color in items:
        style = f' style="color:{color};border-color:{color};"' if color else ""
        pills.append(f'<span class="atlas-pill"{style}>{_esc(label)}: <b>{_esc(value)}</b></span>')
    return f'<div class="atlas-status-bar">{"".join(pills)}</div>'
