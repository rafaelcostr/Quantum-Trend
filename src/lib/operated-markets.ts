export type OperatedMarket = {
  base: string;
  quote: "USDT";
  pair: string;
  label: string;
};

export const OPERATED_MARKETS: OperatedMarket[] = [
  { base: "BTC", quote: "USDT", pair: "BTC/USDT", label: "Bitcoin" },
  { base: "ETH", quote: "USDT", pair: "ETH/USDT", label: "Ethereum" },
];

export const MARKET_TIMEFRAMES = ["1h", "4h", "1d"] as const;
export type MarketTimeframe = (typeof MARKET_TIMEFRAMES)[number];

export function marketTimeframeLabel(tf: MarketTimeframe): string {
  if (tf === "1h") return "1H";
  if (tf === "4h") return "4H";
  return "1D";
}
