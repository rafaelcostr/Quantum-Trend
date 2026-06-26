/** Indicadores alinhados ao pipeline atlas/core/indicators.py (BB 20·2, EMA 20/200, ST 10·3, ADX/RSI 14). */
export type TvStudy = {
  id: string;
  inputs?: Record<string, number | string>;
};

export const STRATEGY_TV_STUDIES: TvStudy[] = [
  { id: "MAExp@tv-basicstudies", inputs: { length: 20 } },
  { id: "MAExp@tv-basicstudies", inputs: { length: 200 } },
  { id: "BB@tv-basicstudies", inputs: { length: 20, mult: 2 } },
  { id: "Supertrend@tv-basicstudies", inputs: { length: 10, factor: 3 } },
  { id: "ADX@tv-basicstudies", inputs: { length: 14 } },
  { id: "RSI@tv-basicstudies", inputs: { length: 14 } },
];

export const STRATEGY_TV_STUDIES_OVERRIDES: Record<string, string | number> = {
  "moving average exponential.plot.linewidth": 2,
  "moving average exponential.plot.color": "#38bdf8",
  "moving average exponential_1.plot.color": "#fbbf24",
  "moving average exponential_1.plot.linewidth": 2,
  "bollinger bands.median.color": "#a78bfa",
  "bollinger bands.upper.color": "#818cf8",
  "bollinger bands.lower.color": "#818cf8",
  "supertrend.up arrow.color": "#22c55e",
  "supertrend.down arrow.color": "#ef4444",
};

export type StrategyChartGuide = {
  id: string;
  label: string;
  category: "bull" | "bear" | "range" | "core";
  indicators: string[];
};

/** Mapa rápido: estratégia → indicadores visíveis no gráfico. */
export const STRATEGY_CHART_GUIDE: StrategyChartGuide[] = [
  { id: "quantum_trend_pro", label: "QuantumTrend Pro", category: "core", indicators: ["EMA 20", "EMA 200", "Supertrend", "ADX"] },
  { id: "pullback_ema20_v1", label: "Pullback EMA20", category: "bull", indicators: ["EMA 20", "EMA 200"] },
  { id: "breakout_high20_v1", label: "Breakout High20", category: "bull", indicators: ["EMA 20", "ADX"] },
  { id: "supertrend_mm200_v1", label: "Supertrend + EMA200", category: "bull", indicators: ["Supertrend", "EMA 200", "ADX"] },
  { id: "mm200_trend_v1", label: "MM200 Trend v1", category: "bull", indicators: ["EMA 200"] },
  { id: "mm200_trend_v2", label: "MM200 Trend v2", category: "bull", indicators: ["EMA 200"] },
  { id: "mm200_daily_macro_v1", label: "MM200 Daily Macro", category: "bull", indicators: ["EMA 200"] },
  { id: "pullback_short_v1", label: "Pullback Short", category: "bear", indicators: ["EMA 20", "EMA 200", "ADX"] },
  { id: "breakout_down_v1", label: "Breakout Down", category: "bear", indicators: ["EMA 200", "ADX"] },
  { id: "supertrend_bear_v1", label: "Supertrend Bear", category: "bear", indicators: ["Supertrend", "EMA 200", "ADX"] },
  { id: "range_hunter_v1", label: "Range Hunter", category: "range", indicators: ["Bollinger", "RSI", "ADX"] },
  { id: "bb_squeeze_v1", label: "BB Squeeze", category: "range", indicators: ["Bollinger", "ADX"] },
  { id: "regime_switching_v1", label: "Regime Switching", category: "range", indicators: ["Bollinger", "ADX", "RSI"] },
];

export const CHART_INDICATOR_LEGEND = [
  { key: "ema20", label: "EMA 20", color: "bg-sky-400", hint: "Pullback · entradas táticas" },
  { key: "ema200", label: "EMA 200", color: "bg-amber-400", hint: "MM200 · filtro de tendência" },
  { key: "bb", label: "Bollinger 20·2", color: "bg-indigo-400", hint: "Range Hunter · BB Squeeze" },
  { key: "st", label: "Supertrend 10·3", color: "bg-emerald-400", hint: "Supertrend Bull/Bear" },
  { key: "adx", label: "ADX 14", color: "bg-orange-400", hint: "Regime · força da tendência" },
  { key: "rsi", label: "RSI 14", color: "bg-pink-400", hint: "Range · sobrecompra/venda" },
] as const;

export function tvInterval(timeframe: string): string {
  const tf = timeframe.toLowerCase();
  if (tf === "1d" || tf === "d") return "D";
  if (tf === "4h") return "240";
  if (tf === "1h") return "60";
  if (tf === "15m") return "15";
  return "240";
}

export function tvBinanceSymbol(symbol: string): string {
  if (symbol.includes(":")) return symbol;
  return `BINANCE:${symbol.replace("/", "")}`;
}

export function tradingViewChartUrl(symbol: string, timeframe: string): string {
  const params = new URLSearchParams({
    symbol: tvBinanceSymbol(symbol),
    interval: tvInterval(timeframe),
  });
  return `https://www.tradingview.com/chart/?${params.toString()}`;
}

export function buildAdvancedChartConfig(symbol: string, timeframe: string) {
  return {
    autosize: true,
    symbol: tvBinanceSymbol(symbol),
    interval: tvInterval(timeframe),
    timezone: "America/Sao_Paulo",
    theme: "dark",
    style: "1",
    locale: "br",
    backgroundColor: "rgba(5, 8, 16, 1)",
    gridColor: "rgba(255, 255, 255, 0.06)",
    hide_top_toolbar: false,
    hide_side_toolbar: false,
    hide_legend: false,
    withdateranges: true,
    allow_symbol_change: false,
    save_image: false,
    calendar: false,
    hide_volume: false,
    show_popup_button: true,
    popup_width: "1000",
    popup_height: "650",
    support_host: "https://www.tradingview.com",
    studies: STRATEGY_TV_STUDIES,
    studies_overrides: STRATEGY_TV_STUDIES_OVERRIDES,
  };
}
