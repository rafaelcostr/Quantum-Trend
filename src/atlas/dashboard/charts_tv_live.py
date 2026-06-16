from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd
import streamlit.components.v1 as components

from atlas.dashboard.performance import TradeMarker


def _to_unix(ts) -> int:
    if hasattr(ts, "timestamp"):
        return int(ts.timestamp())
    return int(pd.Timestamp(ts).timestamp())


def _binance_stream_symbol(symbol: str) -> str:
    """BTC/USDT -> btcusdt"""
    return re.sub(r"[^a-z0-9]", "", symbol.lower())


def _binance_interval(timeframe: str) -> str:
    tf = timeframe.strip().lower()
    allowed = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"}
    if tf in allowed:
        return tf
    return "4h"


def render_tradingview_live_chart(
    df: pd.DataFrame,
    markers: list[TradeMarker],
    *,
    symbol: str = "BTC/USDT",
    timeframe: str = "4h",
    bars: int = 120,
    height: int = 620,
) -> None:
    """Grafico ao vivo via WebSocket Binance + Lightweight Charts."""
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
    tv_markers: list[dict[str, Any]] = []
    if candles:
        window_start = candles[0]["time"]
        window_end = candles[-1]["time"]
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

    stream_sym = _binance_stream_symbol(symbol)
    interval = _binance_interval(timeframe)
    payload = json.dumps(
        {
            "candles": candles,
            "markers": tv_markers,
            "stream": f"{stream_sym}@kline_{interval}",
            "maxBars": bars,
        }
    )

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    body {{ margin: 0; background: #0d1117; }}
    #wrap {{ position: relative; }}
    #chart {{ width: 100%; height: {height}px; }}
    .legend {{
      position: absolute; top: 8px; left: 12px; z-index: 10;
      color: #8b949e; font: 12px/1.4 -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    .legend span {{ margin-right: 14px; }}
    .live {{
      color: #3fb950; font-weight: 600;
    }}
    .live.off {{ color: #f85149; }}
    .dot {{
      display: inline-block; width: 8px; height: 8px; border-radius: 50%;
      background: #3fb950; margin-right: 4px;
      animation: pulse 1.5s infinite;
    }}
    .dot.off {{ background: #f85149; animation: none; }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.35; }}
    }}
    .mm20 {{ color: #58a6ff; }}
    .mm200 {{ color: #f0883e; }}
    #price-tag {{
      position: absolute; top: 8px; right: 12px; z-index: 10;
      color: #e6edf3; font: 14px/1.4 monospace;
    }}
  </style>
</head>
<body>
  <div id="wrap">
    <div class="legend">
      <span class="live"><span class="dot" id="live-dot"></span><span id="live-txt">AO VIVO</span></span>
      <span class="mm20">● MM20</span>
      <span class="mm200">● MM200</span>
      <span>▲ Entrada</span>
      <span>▼ Saida</span>
    </div>
    <div id="price-tag">—</div>
    <div id="chart"></div>
  </div>
  <script>
    const cfg = {payload};
    let candles = cfg.candles.slice();
    const maxBars = cfg.maxBars || 120;

    const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
      layout: {{ background: {{ color: '#0d1117' }}, textColor: '#e6edf3' }},
      grid: {{ vertLines: {{ color: '#21262d' }}, horzLines: {{ color: '#21262d' }} }},
      crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
      rightPriceScale: {{ borderColor: '#30363d' }},
      timeScale: {{ borderColor: '#30363d', timeVisible: true, secondsVisible: false }},
    }});

    const candleSeries = chart.addCandlestickSeries({{
      upColor: '#26a69a', downColor: '#ef5350',
      borderUpColor: '#26a69a', borderDownColor: '#ef5350',
      wickUpColor: '#26a69a', wickDownColor: '#ef5350',
    }});
    candleSeries.setData(candles);
    if (cfg.markers.length) candleSeries.setMarkers(cfg.markers);

    const mm20Series = chart.addLineSeries({{ color: '#58a6ff', lineWidth: 2, title: 'MM20' }});
    const mm200Series = chart.addLineSeries({{ color: '#f0883e', lineWidth: 2, title: 'MM200' }});

    function sma(period) {{
      const out = [];
      for (let i = period - 1; i < candles.length; i++) {{
        let sum = 0;
        for (let j = 0; j < period; j++) sum += candles[i - j].close;
        out.push({{ time: candles[i].time, value: sum / period }});
      }}
      return out;
    }}

    function refreshIndicators() {{
      mm20Series.setData(sma(20));
      mm200Series.setData(sma(200));
    }}
    refreshIndicators();
    chart.timeScale().fitContent();

    const priceTag = document.getElementById('price-tag');
    const liveDot = document.getElementById('live-dot');
    const liveTxt = document.getElementById('live-txt');

    function setLive(on) {{
      liveDot.classList.toggle('off', !on);
      liveTxt.classList.toggle('off', !on);
      liveTxt.textContent = on ? 'AO VIVO' : 'RECONECTANDO...';
    }}

    function applyKline(k) {{
      const candle = {{
        time: Math.floor(k.t / 1000),
        open: parseFloat(k.o),
        high: parseFloat(k.h),
        low: parseFloat(k.l),
        close: parseFloat(k.c),
      }};
      priceTag.textContent = '$' + candle.close.toLocaleString('en-US', {{maximumFractionDigits: 2}});

      const last = candles[candles.length - 1];
      if (last && last.time === candle.time) {{
        candles[candles.length - 1] = candle;
        candleSeries.update(candle);
      }} else if (!last || candle.time > last.time) {{
        candles.push(candle);
        if (candles.length > maxBars) candles.shift();
        candleSeries.update(candle);
      }} else {{
        return;
      }}
      refreshIndicators();
    }}

    let ws = null;
    let retryMs = 1000;

    function connect() {{
      if (ws) {{ try {{ ws.close(); }} catch(e) {{}} }}
      ws = new WebSocket('wss://stream.binance.com:9443/ws/' + cfg.stream);
      ws.onopen = () => {{
        setLive(true);
        retryMs = 1000;
      }};
      ws.onmessage = (ev) => {{
        try {{
          const msg = JSON.parse(ev.data);
          if (msg.k) applyKline(msg.k);
        }} catch(e) {{}}
      }};
      ws.onerror = () => setLive(false);
      ws.onclose = () => {{
        setLive(false);
        setTimeout(connect, retryMs);
        retryMs = Math.min(retryMs * 2, 30000);
      }};
    }}
    connect();

    if (candles.length) {{
      const c = candles[candles.length - 1];
      priceTag.textContent = '$' + c.close.toLocaleString('en-US', {{maximumFractionDigits: 2}});
    }}

    new ResizeObserver(entries => {{
      const w = entries[0].contentRect.width;
      chart.applyOptions({{ width: w, height: {height} }});
    }}).observe(document.getElementById('chart'));
  </script>
</body>
</html>
"""
    components.html(html, height=height + 10, scrolling=False)
