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
  { label: "Buy", color: "bg-success", symbol: "🟢 BUY" },
  { label: "Sell", color: "bg-destructive", symbol: "🔴 SELL" },
  { label: "Stop", color: "bg-warning", symbol: "🟡 STOP" },
  { label: "Trailing", color: "bg-primary", symbol: "🔵 TRAILING" },
  { label: "Pullback", color: "bg-success/70", symbol: "🟢 PULLBACK" },
  { label: "Breakout", color: "bg-purple-500", symbol: "🟣 BREAKOUT" },
  { label: "Supertrend", color: "bg-sky-500", symbol: "🔵 SUPERTREND" },
];

function priceY(price: number, min: number, max: number): string {
  const pct = max === min ? 50 : ((max - price) / (max - min)) * 100;
  return `${Math.max(4, Math.min(96, pct))}%`;
}

function TradeLevelOverlay({ trade, refPrice }: { trade: TradeOverlay; refPrice: number }) {
  const stop = trade.stop ?? trade.entry * 0.98;
  const target = trade.target ?? trade.entry * 1.03;
  const prices = [stop, trade.entry, target, refPrice, trade.trailing].filter(Boolean) as number[];
  const min = Math.min(...prices) * 0.996;
  const max = Math.max(...prices) * 1.004;

  const entryY = priceY(trade.entry, min, max);
  const stopY = priceY(stop, min, max);
  const targetY = priceY(target, min, max);
  const trailY = trade.trailing ? priceY(trade.trailing, min, max) : null;

  const profitTop = Math.min(parseFloat(entryY), parseFloat(targetY));
  const profitBottom = Math.max(parseFloat(entryY), parseFloat(targetY));
  const riskTop = Math.min(parseFloat(entryY), parseFloat(stopY));
  const riskBottom = Math.max(parseFloat(entryY), parseFloat(stopY));

  return (
    <div className="absolute inset-0 pointer-events-none z-10 pl-2 pr-14">
      <div
        className="absolute left-0 right-0 bg-success/10 border-y border-success/20"
        style={{ top: `${profitTop}%`, height: `${profitBottom - profitTop}%` }}
      />
      <div
        className="absolute left-0 right-0 bg-destructive/10 border-y border-destructive/20"
        style={{ top: `${riskTop}%`, height: `${riskBottom - riskTop}%` }}
      />

      <div className="absolute left-0 right-0 border-t-2 border-dashed border-success" style={{ top: targetY }}>
        <span className="absolute right-0 -top-3 text-[10px] font-mono text-success bg-black/60 px-1 rounded">TP</span>
      </div>
      <div className="absolute left-0 right-0 border-t-2 border-success" style={{ top: entryY }}>
        <span className="absolute left-2 -top-4 text-[11px] font-bold text-success bg-black/70 px-2 py-0.5 rounded">
          BUY ${trade.entry.toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </span>
      </div>
      <div className="absolute left-0 right-0 border-t-2 border-dashed border-warning" style={{ top: stopY }}>
        <span className="absolute right-0 -top-3 text-[10px] font-mono text-warning bg-black/60 px-1 rounded">SL</span>
      </div>
      {trailY && (
        <div className="absolute left-0 right-0 border-t border-dotted border-primary" style={{ top: trailY }}>
          <span className="absolute right-12 -top-3 text-[10px] font-mono text-primary bg-black/60 px-1 rounded">
            TRAIL
          </span>
        </div>
      )}

      <div className="absolute right-0 top-1/2 -translate-y-1/2 flex flex-col items-end gap-6 text-[10px] font-mono pr-1">
        <div className="text-success">│ TP</div>
        <div className="text-success font-bold">├── BUY</div>
        <div className="text-warning">└── SL</div>
      </div>
    </div>
  );
}

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
    wrap.style.height = "360px";
    wrap.style.width = "100%";
    const inner = document.createElement("div");
    inner.className = "tradingview-widget-container__widget";
    inner.style.height = "360px";
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
  const refPrice = price ?? active?.current ?? active?.entry;

  return (
    <Panel
      className="p-0 overflow-hidden"
      title="Gráfico ao vivo"
      subtitle="TradingView · BTCUSDT · EMA20 · EMA200 · Supertrend · Volume"
      action={
        price != null ? (
          <span className="chip num text-sm">${price.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
        ) : null
      }
    >
      <div className="flex flex-col lg:flex-row lg:items-stretch">
        <div className="relative w-full lg:flex-1 h-[280px] sm:h-[320px] xl:h-[360px] shrink-0 border-b lg:border-b-0 lg:border-r border-white/5 overflow-hidden">
          <div ref={containerRef} className="absolute inset-0 h-full w-full" />
          {active && refPrice != null && <TradeLevelOverlay trade={active} refPrice={refPrice} />}
        </div>

        <aside className="w-full lg:w-48 xl:w-52 shrink-0 p-3 space-y-3 bg-black/20 max-h-[280px] sm:max-h-[320px] xl:max-h-[360px] overflow-y-auto">
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

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 text-[10px] space-y-1">
            <div className="font-semibold text-muted-foreground uppercase mb-1">Legenda de zonas</div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded bg-success/20 border border-success/40" />
              <span>Lucro potencial</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded bg-destructive/20 border border-destructive/40" />
              <span>Risco</span>
            </div>
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
                  <div className="text-xs font-medium">🟢 {t.strategy}</div>
                  <div className="mt-2 space-y-1 text-[10px] font-mono">
                    <div className="flex justify-between text-success">
                      <span>BUY</span>
                      <span>${t.entry.toLocaleString()}</span>
                    </div>
                    {t.target && (
                      <div className="flex justify-between text-primary">
                        <span>TP</span>
                        <span>${t.target.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                      </div>
                    )}
                    {t.stop && (
                      <div className="flex justify-between text-warning">
                        <span>SL</span>
                        <span>${t.stop.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                      </div>
                    )}
                    {t.trailing && (
                      <div className="flex justify-between text-sky-400">
                        <span>Trail</span>
                        <span>${t.trailing.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
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
            <p className="text-[11px] text-muted-foreground">
              Sem posição — níveis BUY · TP · SL aparecem após entrada.
            </p>
          )}

          {active && (
            <div className="rounded-xl border border-primary/30 bg-primary/5 p-3 text-[11px] space-y-1">
              <div className="font-semibold text-primary">Trade ativo</div>
              <div>Estratégia: {active.strategy}</div>
              {active.score != null && <div>Score: {Math.round(active.score)}</div>}
              <div>Regime: {active.regime ?? "—"}</div>
              <div className={active.pnlPct >= 0 ? "text-success" : "text-destructive"}>
                P&L: {active.pnlPct >= 0 ? "+" : ""}
                {active.pnlPct.toFixed(2)}%
              </div>
            </div>
          )}
        </aside>
      </div>
    </Panel>
  );
}
