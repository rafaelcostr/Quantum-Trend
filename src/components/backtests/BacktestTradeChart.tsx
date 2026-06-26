import { useEffect, useRef } from "react";
import {
  ColorType,
  createChart,
  type CandlestickData,
  type SeriesMarker,
  type Time,
} from "lightweight-charts";
import type { BacktestChartMarker, BacktestChartResponse } from "@/lib/api";

type Props = {
  data: BacktestChartResponse;
  className?: string;
};

function toTime(ms: number): Time {
  return Math.floor(ms / 1000) as Time;
}

function chartMarkers(markers: BacktestChartMarker[]): SeriesMarker<Time>[] {
  return markers.map((m) => {
    const win = m.win;
    const isEntry = m.kind === "entry";
    const isShort = m.side === "short";
    const color = win ? "#22c55e" : "#ef4444";

    let position: "aboveBar" | "belowBar" = "belowBar";
    let shape: "arrowUp" | "arrowDown" | "circle" = "arrowUp";

    if (isEntry) {
      if (isShort) {
        position = "aboveBar";
        shape = "arrowDown";
      } else {
        position = "belowBar";
        shape = "arrowUp";
      }
    } else {
      position = isShort ? "belowBar" : "aboveBar";
      shape = "circle";
    }

    const prefix = isEntry ? "E" : "X";
    const text = m.label ? `${prefix} ${m.label}` : prefix;

    return {
      time: toTime(m.t),
      position,
      shape,
      color,
      text,
      size: isEntry ? 1 : 0.75,
    };
  });
}

export function BacktestTradeChart({ data, className }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap || !data.bars.length) return;

    wrap.innerHTML = "";
    const container = document.createElement("div");
    container.style.width = "100%";
    container.style.height = "100%";
    wrap.appendChild(container);

    const chart = createChart(container, {
      width: wrap.clientWidth,
      height: wrap.clientHeight || 520,
      layout: {
        background: { type: ColorType.Solid, color: "rgba(5, 8, 16, 1)" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.06)" },
        horzLines: { color: "rgba(255,255,255,0.06)" },
      },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
      timeScale: { borderColor: "rgba(255,255,255,0.08)", timeVisible: true, secondsVisible: false },
      crosshair: { mode: 1 },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    const candles: CandlestickData<Time>[] = data.bars.map((b) => ({
      time: toTime(b.t),
      open: b.o,
      high: b.h,
      low: b.l,
      close: b.c,
    }));

    candleSeries.setData(candles);

    if (data.markers.length > 0) {
      candleSeries.setMarkers(chartMarkers(data.markers));
    }

    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: wrap.clientWidth, height: wrap.clientHeight || 520 });
    });
    ro.observe(wrap);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [data]);

  if (!data.bars.length) {
    return (
      <div className={className ?? "h-[520px] flex items-center justify-center text-sm text-muted-foreground px-6 text-center"}>
        {data.error ?? "Sem candles para este backtest."}
      </div>
    );
  }

  return <div ref={wrapRef} className={className ?? "h-[520px] w-full"} />;
}
