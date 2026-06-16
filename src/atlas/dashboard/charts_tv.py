from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit.components.v1 as components

from atlas.dashboard.performance import TradeMarker


def _to_unix(ts) -> int:
    if hasattr(ts, "timestamp"):
        return int(ts.timestamp())
    return int(pd.Timestamp(ts).timestamp())


def render_tradingview_chart(
    df: pd.DataFrame,
    markers: list[TradeMarker],
    bars: int = 120,
    height: int = 620,
) -> None:
    """Embed TradingView Lightweight Charts (professional candlestick UI)."""
    view = df.tail(bars).copy()
    candles = [
        {
            "time": _to_unix(idx),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }
        for idx, row in view.iterrows()
    ]
    mm200 = [
        {"time": _to_unix(idx), "value": float(row["mm200"])}
        for idx, row in view.iterrows()
        if pd.notna(row.get("mm200"))
    ]
    mm20 = [
        {"time": _to_unix(idx), "value": float(row["mm20"])}
        for idx, row in view.iterrows()
        if pd.notna(row.get("mm20"))
    ]
    tv_markers: list[dict[str, Any]] = []
    window_start = _to_unix(view.index[0])
    window_end = _to_unix(view.index[-1])
    for m in markers:
        t = _to_unix(m.time)
        if t < window_start or t > window_end:
            continue
        tv_markers.append(
            {
                "time": t,
                "position": "belowBar" if m.side == "buy" else "aboveBar",
                "color": "#3fb950" if m.side == "buy" else "#f85149",
                "shape": "arrowUp" if m.side == "buy" else "arrowDown",
                "text": m.label[:24],
            }
        )

    payload = json.dumps(
        {
            "candles": candles,
            "mm200": mm200,
            "mm20": mm20,
            "markers": tv_markers,
        }
    )

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    body {{ margin: 0; background: #0d1117; }}
    #chart {{ width: 100%; height: {height}px; }}
    .legend {{
      position: absolute; top: 8px; left: 12px; z-index: 10;
      color: #8b949e; font: 12px/1.4 -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    .legend span {{ margin-right: 14px; }}
    .mm20 {{ color: #58a6ff; }}
    .mm200 {{ color: #f0883e; }}
  </style>
</head>
<body>
  <div class="legend">
    <span class="mm20">● MM20</span>
    <span class="mm200">● MM200</span>
    <span>▲ Entrada</span>
    <span>▼ Saída</span>
  </div>
  <div id="chart"></div>
  <script>
    const data = {payload};
    const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
      layout: {{ background: {{ color: '#0d1117' }}, textColor: '#e6edf3' }},
      grid: {{ vertLines: {{ color: '#21262d' }}, horzLines: {{ color: '#21262d' }} }},
      crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
      rightPriceScale: {{ borderColor: '#30363d' }},
      timeScale: {{ borderColor: '#30363d', timeVisible: true, secondsVisible: false }},
    }});
    const candles = chart.addCandlestickSeries({{
      upColor: '#26a69a', downColor: '#ef5350',
      borderUpColor: '#26a69a', borderDownColor: '#ef5350',
      wickUpColor: '#26a69a', wickDownColor: '#ef5350',
    }});
    candles.setData(data.candles);
    if (data.markers.length) candles.setMarkers(data.markers);

    const mm20 = chart.addLineSeries({{ color: '#58a6ff', lineWidth: 2, title: 'MM20' }});
    if (data.mm20.length) mm20.setData(data.mm20);

    const mm200 = chart.addLineSeries({{ color: '#f0883e', lineWidth: 2, title: 'MM200' }});
    if (data.mm200.length) mm200.setData(data.mm200);

    chart.timeScale().fitContent();
    new ResizeObserver(entries => {{
      const w = entries[0].contentRect.width;
      chart.applyOptions({{ width: w, height: {height} }});
    }}).observe(document.getElementById('chart'));
  </script>
</body>
</html>
"""
    components.html(html, height=height + 10, scrolling=False)
