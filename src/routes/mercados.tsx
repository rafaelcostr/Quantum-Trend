import { lazy, Suspense, useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { ExternalLink, LineChart, Loader2 } from "lucide-react";
import { MarketChartLegend } from "@/components/markets/MarketChartLegend";
import { PageHeader, Panel } from "@/components/ui/page";
import { EmptyState, InlineError, StaleBadge } from "@/components/ui/query-state";
import { cn } from "@/lib/utils";
import {
  MARKET_TIMEFRAMES,
  OPERATED_MARKETS,
  type MarketTimeframe,
  marketTimeframeLabel,
} from "@/lib/operated-markets";
import { isBrowser, useMarketChart, useMarkets } from "@/lib/queries";
import { tradingViewChartUrl } from "@/lib/tradingview-chart";
import type { MarketTicker } from "@/lib/api";

const StrategyMarketChart = lazy(() =>
  import("@/components/markets/StrategyMarketChart").then((module) => ({
    default: module.StrategyMarketChart,
  })),
);

export const Route = createFileRoute("/mercados")({
  head: () => ({ meta: [{ title: "Mercados · Quantum-Trend" }] }),
  component: Page,
});

function formatPrice(price: number): string {
  return price.toLocaleString(undefined, { maximumFractionDigits: price < 1 ? 4 : 2 });
}

function PairCard({
  market,
  ticker,
  loading,
  selected,
  onSelect,
}: {
  market: (typeof OPERATED_MARKETS)[number];
  ticker?: MarketTicker;
  loading: boolean;
  selected: boolean;
  onSelect: () => void;
}) {
  const up = (ticker?.change_pct ?? 0) >= 0;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "glass rounded-2xl p-5 text-left w-full transition hover:scale-[1.01] hover:border-primary/40 border",
        selected ? "border-primary/60 ring-2 ring-primary/30 bg-primary/5" : "border-transparent",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold text-lg">{market.pair}</div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            {market.label} · Spot Binance
          </div>
        </div>
        {ticker ? (
          <span className={cn("chip shrink-0", up ? "text-success" : "text-destructive")}>
            {up ? "+" : ""}
            {ticker.change_pct.toFixed(2)}%
          </span>
        ) : loading ? (
          <span className="chip shrink-0 text-muted-foreground animate-pulse">…</span>
        ) : null}
      </div>

      <div className="num text-3xl mt-4">{ticker ? `$${formatPrice(ticker.price)}` : "—"}</div>

      <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
        <LineChart className="h-3.5 w-3.5" />
        Clique para ver candles + EMA20 + EMA200 + Bollinger + Supertrend
      </div>
    </button>
  );
}

function ChartBlock({
  base,
  pair,
  timeframe,
  price,
}: {
  base: string;
  pair: string;
  timeframe: MarketTimeframe;
  price?: number;
}) {
  const chart = useMarketChart(base, timeframe, true);
  const tvUrl = tradingViewChartUrl(pair, timeframe);

  return (
    <Panel
      className="p-0 overflow-hidden"
      title={`Gráfico · ${pair}`}
      subtitle="Candles · EMA20 · EMA200 · Bollinger 20·2 · Supertrend 10·3"
      action={
        <div className="flex items-center gap-2 flex-wrap justify-end">
          {price != null && (
            <span className="chip num text-sm hidden sm:inline-flex">${formatPrice(price)}</span>
          )}
          <StaleBadge stale={chart.data?.stale} lastSuccessAt={chart.data?.last_success_at} />
          <a
            href={tvUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs hover:bg-white/10"
          >
            Abrir no TradingView
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      }
    >
      {chart.isPending && !chart.data ? (
        <div className="h-[560px] flex flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
          Carregando candles e indicadores…
        </div>
      ) : chart.isError || !chart.data ? (
        <div className="h-[560px] flex items-center justify-center px-6">
          <InlineError error={chart.error} title="Erro ao carregar gráfico" className="max-w-md" />
        </div>
      ) : chart.data.bars.length === 0 ? (
        <div className="h-[560px] flex items-center justify-center px-6">
          <EmptyState
            title="Sem candles disponíveis"
            detail="A API respondeu, mas não retornou histórico para este par e timeframe."
          />
        </div>
      ) : (
        <Suspense
          fallback={
            <div className="h-[560px] flex flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
              Preparando gráfico...
            </div>
          }
        >
          <StrategyMarketChart
            key={`${pair}-${timeframe}`}
            data={chart.data}
            className="h-[560px] w-full"
          />
        </Suspense>
      )}
      <MarketChartLegend />
    </Panel>
  );
}

function Page() {
  const markets = useMarkets();
  const [openedPair, setOpenedPair] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState<MarketTimeframe>("4h");

  const tickerByBase = useMemo(() => {
    const map = new Map<string, MarketTicker>();
    for (const item of markets.data?.items ?? []) {
      map.set(item.symbol.toUpperCase(), item);
    }
    return map;
  }, [markets.data?.items]);

  const selectedMarket = openedPair
    ? (OPERATED_MARKETS.find((m) => m.pair === openedPair) ?? OPERATED_MARKETS[0])
    : null;
  const selectedTicker = selectedMarket ? tickerByBase.get(selectedMarket.base) : undefined;

  if (!isBrowser) {
    return <div className="text-muted-foreground text-sm">Carregando mercados…</div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mercados"
        subtitle="BTC/USDT e ETH/USDT — gráfico nativo com os mesmos indicadores calculados no backtest."
        actions={
          <StaleBadge
            stale={markets.data?.cache?.stale}
            lastSuccessAt={markets.data?.cache?.last_success_at}
          />
        }
      />

      {markets.isError && !markets.data && (
        <InlineError
          error={markets.error}
          title="API de mercados indisponível"
          className="max-w-2xl"
        />
      )}

      <Panel>
        {!markets.isPending && !markets.data?.items.length ? (
          <EmptyState
            title="Sem cotações disponíveis"
            detail="A lista de mercados veio vazia. Verifique conexão, Binance ou configuração de símbolos."
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {OPERATED_MARKETS.map((market) => (
              <PairCard
                key={market.pair}
                market={market}
                ticker={tickerByBase.get(market.base)}
                loading={markets.isPending && !markets.data}
                selected={openedPair === market.pair}
                onSelect={() => setOpenedPair(market.pair)}
              />
            ))}
          </div>
        )}
      </Panel>

      {selectedMarket ? (
        <div className="space-y-3">
          <div className="flex rounded-lg border border-white/10 overflow-hidden w-fit">
            {MARKET_TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                type="button"
                onClick={() => setTimeframe(tf)}
                className={cn(
                  "px-4 py-2 text-xs font-medium transition",
                  timeframe === tf
                    ? "bg-primary text-white"
                    : "bg-white/5 text-muted-foreground hover:bg-white/10",
                )}
              >
                {marketTimeframeLabel(tf)}
              </button>
            ))}
          </div>
          <ChartBlock
            base={selectedMarket.base}
            pair={selectedMarket.pair}
            timeframe={timeframe}
            price={selectedTicker?.price}
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-white/15 bg-white/[0.02] px-6 py-10 text-center text-sm text-muted-foreground">
          Selecione <strong className="text-foreground">BTC/USDT</strong> ou{" "}
          <strong className="text-foreground">ETH/USDT</strong> para carregar o gráfico com médias,
          bandas de Bollinger e Supertrend.
        </div>
      )}
    </div>
  );
}
