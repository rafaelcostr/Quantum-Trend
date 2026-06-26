import { useEffect, useRef } from "react";
import { buildAdvancedChartConfig } from "@/lib/tradingview-chart";

type Props = {
  symbol: string;
  timeframe: string;
  className?: string;
};

export function MarketTradingViewEmbed({ symbol, timeframe, className }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;

    root.innerHTML = "";

    const widget = document.createElement("div");
    widget.className = "tradingview-widget-container__widget";
    widget.style.height = "100%";
    widget.style.width = "100%";

    const script = document.createElement("script");
    script.type = "text/javascript";
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.async = true;
    script.innerHTML = JSON.stringify(buildAdvancedChartConfig(symbol, timeframe));

    root.appendChild(widget);
    root.appendChild(script);
  }, [symbol, timeframe]);

  return (
    <div
      ref={containerRef}
      className={`tradingview-widget-container ${className ?? "h-full w-full min-h-[520px]"}`}
    />
  );
}
