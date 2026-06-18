import { lazy, Suspense } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { LineChart, Rocket } from "lucide-react";
import { LiveTerminalHeader } from "@/components/operations/LiveTerminalHeader";
import { PositionsPnLPanel } from "@/components/operations/PositionsPnLPanel";
import { RuntimeTimeline } from "@/components/operations/RuntimeTimeline";
import { StrategyRuntimeCards } from "@/components/operations/StrategyRuntimeCards";
import { PageHeader } from "@/components/ui/page";
import {
  buildOpsStats,
  buildStrategyCards,
  buildTimelineEvents,
  buildTradeOverlays,
} from "@/lib/operations-terminal";
import {
  useBotToggle,
  useJournal,
  useMarkets,
  useOperationsFeed,
  usePlatformStatus,
  usePositions,
  useQuantumStatus,
  useRisk,
  useSettings,
} from "@/lib/queries";

const LiveTradingViewChart = lazy(() =>
  import("@/components/operations/LiveTradingViewChart").then((m) => ({ default: m.LiveTradingViewChart })),
);

export const Route = createFileRoute("/operacoes")({
  head: () => ({
    meta: [
      { title: "Operações ao Vivo · Quantum-Trend" },
      { name: "description", content: "Terminal quantitativo em tempo real — gráfico, estratégias, timeline e P&L." },
    ],
  }),
  component: OperationsTerminalPage,
});

function ChartSkeleton() {
  return (
    <div className="glass rounded-2xl min-h-[420px] flex items-center justify-center text-sm text-muted-foreground">
      Carregando gráfico TradingView…
    </div>
  );
}

function OperationsTerminalPage() {
  const feed = useOperationsFeed();
  const pos = usePositions();
  const journal = useJournal();
  const markets = useMarkets();
  const risk = useRisk();
  const settings = useSettings();
  const quantum = useQuantumStatus();
  const platform = usePlatformStatus();
  const bot = useBotToggle();

  if (feed.isLoading && !feed.data) {
    return <div className="text-muted-foreground text-sm py-12 text-center">Conectando ao runtime…</div>;
  }
  if (feed.error || !feed.data) {
    return (
      <div className="text-destructive text-sm space-y-2">
        <p>Erro ao carregar terminal. Confirme a API Python: <code className="text-secondary">python -m atlas.cli api</code></p>
      </div>
    );
  }

  const feedItems = feed.data.items;
  const botSnap = feed.data.bot;
  const mode = feed.data.mode;
  const running = botSnap.running;

  const stats = buildOpsStats(feed.data, quantum.data, platform.data, risk.data);
  const positions = pos.data?.items ?? [];
  const journalItems = journal.data?.items ?? [];

  const active = settings.data?.operational?.active;
  const symbol = active?.symbol ?? botSnap.instances?.[0]?.symbol ?? "BTC/USDT";
  const timeframe = active?.timeframe ?? botSnap.instances?.[0]?.timeframe ?? "4h";

  const btcMarket = markets.data?.items?.find((m) => m.symbol.includes("BTC"));
  const sparkline = btcMarket?.sparkline ?? [];

  const strategyCards = buildStrategyCards(
    botSnap.instances,
    feedItems,
    stats,
    quantum.data,
    platform.data,
    sparkline,
  );
  const timeline = buildTimelineEvents(feedItems, journalItems);
  const tradeOverlays = buildTradeOverlays(positions, journalItems);
  const capital = risk.data?.balance ?? stats.balance;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Operações ao Vivo"
        subtitle="Terminal quantitativo · mercado, estratégias, decisões e P&L em tempo real."
        actions={
          <div className="flex gap-2 flex-wrap">
            <Link
              to="/live"
              className="rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10 inline-flex items-center gap-2"
            >
              <Rocket className="h-4 w-4" />
              Trading Live
            </Link>
            <button
              onClick={() => bot.mutate(running ? "stop" : "start")}
              disabled={bot.isPending || stats.kill_switch}
              className={`rounded-xl px-4 py-2 text-sm font-medium disabled:opacity-50 ${
                running ? "bg-destructive/90 text-white" : "bg-gradient-to-r from-[#7C3AED] to-[#3B82F6] text-white"
              }`}
            >
              {running ? "Parar Bot" : "Iniciar Paper"}
            </button>
          </div>
        }
      />

      {!running && (
        <div className="rounded-xl border border-dashed border-white/15 bg-white/[0.02] px-4 py-3 text-sm text-muted-foreground flex items-center gap-2">
          <LineChart className="h-4 w-4 shrink-0" />
          Inicie o bot para ativar gráfico, cards de estratégia e timeline ao vivo.
        </div>
      )}

      <LiveTerminalHeader
        stats={stats}
        bot={botSnap}
        mode={mode}
        symbol={symbol}
        timeframe={timeframe}
        quantum={quantum.data}
        platform={platform.data}
        nextUpdateSec={feed.data.next_tick_in}
        isStreaming={feed.isStreaming}
      />

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-4 items-start">
        <Suspense fallback={<ChartSkeleton />}>
          <LiveTradingViewChart
            symbol={symbol}
            timeframe={timeframe}
            price={btcMarket?.price}
            trades={tradeOverlays}
          />
        </Suspense>
        <StrategyRuntimeCards cards={strategyCards} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <RuntimeTimeline events={timeline} />
        <PositionsPnLPanel
          positions={positions}
          stats={stats}
          risk={risk.data}
          capital={capital}
          loading={pos.isLoading && !pos.data}
        />
      </div>
    </div>
  );
}
