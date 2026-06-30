import { useEffect, useRef } from "react";
import {
  ColorType,
  createChart,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type Time,
} from "lightweight-charts";
import { formatApiError } from "@/components/ui/query-state";
import type { MarketChartBar, MarketChartResponse } from "@/lib/api";

type Props = {
  data: MarketChartResponse;
  className?: string;
};

function toTime(ms: number): Time {
  return Math.floor(ms / 1000) as Time;
}

function linePoints(bars: MarketChartBar[], key: keyof MarketChartBar): LineData<Time>[] {
  return bars
    .filter((b) => typeof b[key] === "number")
    .map((b) => ({ time: toTime(b.t), value: b[key] as number }));
}

function isCompleteCandle(
  bar: MarketChartBar,
): bar is MarketChartBar & { o: number; h: number; l: number; c: number } {
  return (
    typeof bar.o === "number" &&
    typeof bar.h === "number" &&
    typeof bar.l === "number" &&
    typeof bar.c === "number"
  );
}

export function StrategyMarketChart({ data, className }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

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
      height: wrap.clientHeight || 560,
      layout: {
        background: { type: ColorType.Solid, color: "rgba(5, 8, 16, 1)" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.06)" },
        horzLines: { color: "rgba(255,255,255,0.06)" },
      },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
      timeScale: {
        borderColor: "rgba(255,255,255,0.08)",
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: { mode: 1 },
    });
    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    const series: ISeriesApi<"Line">[] = [
      chart.addLineSeries({
        color: "#38bdf8",
        lineWidth: 2,
        title: "EMA 20",
        priceLineVisible: false,
        lastValueVisible: true,
      }),
      chart.addLineSeries({
        color: "#fbbf24",
        lineWidth: 2,
        title: "EMA 200",
        priceLineVisible: false,
        lastValueVisible: true,
      }),
      chart.addLineSeries({
        color: "#818cf8",
        lineWidth: 1,
        lineStyle: 2,
        title: "BB Sup",
        priceLineVisible: false,
        lastValueVisible: false,
      }),
      chart.addLineSeries({
        color: "#a78bfa",
        lineWidth: 1,
        title: "BB Mid",
        priceLineVisible: false,
        lastValueVisible: false,
      }),
      chart.addLineSeries({
        color: "#818cf8",
        lineWidth: 1,
        lineStyle: 2,
        title: "BB Inf",
        priceLineVisible: false,
        lastValueVisible: false,
      }),
      chart.addLineSeries({
        color: "#34d399",
        lineWidth: 2,
        title: "Supertrend",
        priceLineVisible: false,
        lastValueVisible: true,
      }),
    ];

    const candles: CandlestickData<Time>[] = data.bars.filter(isCompleteCandle).map((b) => ({
      time: toTime(b.t),
      open: b.o,
      high: b.h,
      low: b.l,
      close: b.c,
    }));

    candleSeries.setData(candles);
    const keys: (keyof MarketChartBar)[] = [
      "ema20",
      "ema200",
      "bb_upper",
      "bb_mid",
      "bb_lower",
      "supertrend",
    ];
    keys.forEach((key, i) => series[i]?.setData(linePoints(data.bars, key)));

    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: wrap.clientWidth, height: wrap.clientHeight || 560 });
    });
    ro.observe(wrap);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [data]);

  if (!data.bars.length) {
    return (
      <div
        className={
          className ?? "h-[560px] flex items-center justify-center text-sm text-muted-foreground"
        }
      >
        {data.error ? formatApiError(data.error) : "Sem dados de candles para este par."}
      </div>
    );
  }

  return <div ref={wrapRef} className={className ?? "h-[560px] w-full"} />;
}
