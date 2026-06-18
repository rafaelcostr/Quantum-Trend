import { useEffect, useRef, useState } from "react";
import { Panel } from "@/components/ui/page";
import type { TradeOverlay } from "@/lib/operations-terminal";
import { tvInterval } from "@/lib/operations-terminal";

type Props = {
  symbol: string;
  timeframe: string;
  price?: number;
  trades: TradeOverlay[];
  onSelectTrade?: (trade: TradeOverlay | null) => void;
};

const MARKER_LEGEND = [
  { label: "Entrada", color: "bg-success", symbol: "🟢 BUY" },
  { label: "Saída", color: "bg-destructive", symbol: "🔴 SELL" },
  { label: "Stop", color: "bg-warning", symbol: "🟡 STOP" },
  { label: "Pullback", color: "bg-success/70", symbol: "🟢 PULLBACK" },
  { label: "Breakout", color: "bg-purple-500", symbol: "🟣 BREAKOUT" },
  { label: "Supertrend", color: "bg-primary", symbol: "🔵 SUPERTREND" },
];

export function LiveTradingViewChart({ symbol, timeframe, price, trades, onSelectTrade }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoverTrade, setHoverTrade] = useState<TradeOverlay | null>(null);
  const tvSymbol = symbol.includes(":") ? symbol : `BINANCE:${symbol.replace("/", "")}`;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "tradingview-widget-container";
    wrap.style.height = "100%";
    wrap.style.width = "100%";
    const inner = document.createElement("div");
    inner.className = "tradingview-widget-container__widget";
    inner.style.height = "calc(100% - 32px)";
    inner.style.width = "100%";
    wrap.appendChild(inner);
    const script = document.createElement("script");
    script.type = "text/javascript";
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: tvSymbol,
      interval: tvInterval(timeframe),
      timezone: "America/Sao_Paulo",
      theme: "dark",
      style: "1",
      locale: "br",
      backgroundColor: "rgba(5, 8, 16, 1)",
      gridColor: "rgba(255, 255, 255, 0.06)",
      hide_top_toolbar: false,
      hide_legend: false,
      allow_symbol_change: false,
      save_image: false,
      calendar: false,
      hide_volume: false,
      support_host: "https://www.tradingview.com",
      studies: ["STD;EMA%1%2020", "STD;EMA%1%20200", "STD;Supertrend%1%1"],
    });
    wrap.appendChild(script);
    el.appendChild(wrap);
  }, [tvSymbol, timeframe]);

  const active = hoverTrade ?? trades[0] ?? null;

  return (
    <Panel
      className="h-full min-h-[420px] flex flex-col p-0 overflow-hidden"
      title="Gráfico ao vivo"
      subtitle="TradingView · BTCUSDT · EMA20 · EMA200 · Supertrend · Volume"
      action={
        price != null ? (
          <span className="chip num text-sm">${price.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
        ) : null
      }
    >
      <div className="flex flex-1 min-h-0 flex-col lg:flex-row">
        <div className="relative flex-1 min-h-[360px] border-b lg:border-b-0 lg:border-r border-white/5">
          <div ref={containerRef} className="absolute inset-0" />
        </div>

        <aside className="w-full lg:w-56 shrink-0 p-4 space-y-4 bg-black/20">
          <div>
            <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-2">Overlays</div>
            <ul className="space-y-1.5">
              {MARKER_LEGEND.map((m) => (
                <li key={m.label} className="flex items-center gap-2 text-[11px]">
                  <span className={`h-2 w-2 rounded-full ${m.color}`} />
                  <span className="text-muted-foreground">{m.symbol}</span>
                </li>
              ))}
            </ul>
          </div>

          {trades.length > 0 ? (
            <div className="space-y-2">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Operações abertas</div>
              {trades.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onMouseEnter={() => {
                    setHoverTrade(t);
                    onSelectTrade?.(t);
                  }}
                  onMouseLeave={() => {
                    setHoverTrade(null);
                    onSelectTrade?.(null);
                  }}
                  className="w-full text-left rounded-xl border border-white/10 bg-white/[0.03] p-3 hover:border-primary/40 transition-colors"
                >
                  <div className="text-xs font-medium">{t.strategy}</div>
                  <div className="mt-2 space-y-1 text-[10px] font-mono">
                    <div className="flex justify-between text-success">
                      <span>Entrada</span>
                      <span>${t.entry.toLocaleString()}</span>
                    </div>
                    {t.target && (
                      <div className="flex justify-between text-primary">
                        <span>Take Profit</span>
                        <span>${t.target.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                      </div>
                    )}
                    {t.stop && (
                      <div className="flex justify-between text-warning">
                        <span>Stop</span>
                        <span>${t.stop.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                      </div>
                    )}
                  </div>
                  <div className={`mt-2 text-xs num ${t.pnlPct >= 0 ? "text-success" : "text-destructive"}`}>
                    {t.pnlPct >= 0 ? "+" : ""}
                    {t.pnlPct.toFixed(2)}%
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-muted-foreground">Sem posição — níveis de trade aparecem após entrada.</p>
          )}

          {active && (
            <div className="rounded-xl border border-primary/30 bg-primary/5 p-3 text-[11px] space-y-1">
              <div className="font-semibold text-primary">Hover · Trade</div>
              <div>Estratégia: {active.strategy}</div>
              {active.score != null && <div>Score: {Math.round(active.score)}</div>}
              <div>Regime: {active.regime ?? "—"}</div>
              <div>Risco: ~1%</div>
              <div className={active.pnlPct >= 0 ? "text-success" : "text-destructive"}>
                Resultado: {active.pnlPct >= 0 ? "+" : ""}
                {active.pnlPct.toFixed(2)}%
              </div>
            </div>
          )}
        </aside>
      </div>
    </Panel>
  );
}
