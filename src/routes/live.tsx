import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertTriangle, CheckCircle2, Rocket, ShieldAlert, StopCircle } from "lucide-react";
import { lazy, Suspense, useState } from "react";
import { PageHeader, Panel } from "@/components/ui/page";
import { OperationsFeed } from "@/components/widgets/OperationsFeed";
import { buildTradeOverlays } from "@/lib/operations-terminal";
import {
  useBotToggle,
  useJournal,
  useLive,
  useMarkets,
  useOperationsFeed,
  usePositions,
  useSettings,
} from "@/lib/queries";

const LiveTradingViewChart = lazy(() =>
  import("@/components/operations/LiveTradingViewChart").then((module) => ({
    default: module.LiveTradingViewChart,
  })),
);

export const Route = createFileRoute("/live")({
  head: () => ({
    meta: [
      { title: "Trading Live · Quantum-Trend" },
      { name: "description", content: "Promoção para conta real com gates de segurança." },
    ],
  }),
  component: LivePage,
});

function LivePage() {
  const { data, isLoading, isPending, error } = useLive();
  const feed = useOperationsFeed();
  const positions = usePositions();
  const journal = useJournal();
  const markets = useMarkets();
  const settings = useSettings();
  const bot = useBotToggle();
  const [confirm, setConfirm] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [errMsg, setErrMsg] = useState<string | null>(null);

  if ((isLoading || isPending) && !data)
    return <div className="text-muted-foreground text-sm">Carregando gates live…</div>;
  if (error && !data) {
    const detail = error instanceof Error ? error.message.slice(0, 400) : "Resposta vazia da API.";
    return (
      <div className="text-destructive text-sm space-y-2">
        <p>Erro ao carregar trading live.</p>
        <p className="text-xs text-muted-foreground">{detail}</p>
        <p className="text-xs text-muted-foreground">
          Se o dashboard funciona mas esta página não, pare a API antiga e reinicie:{" "}
          <code className="text-secondary">python -m atlas.cli api</code>
        </p>
      </div>
    );
  }

  const { gates, bot: botSnap, config, instances = botSnap.instances ?? [] } = data;
  const isLive = botSnap.running && botSnap.mode === "live";
  const canStart = gates.eligible && !isLive && !botSnap.running;
  const active = settings.data?.operational?.active;
  const symbol = active?.symbol ?? instances[0]?.symbol ?? config.symbol;
  const timeframe = active?.timeframe ?? instances[0]?.timeframe ?? config.timeframe;
  const base = symbol.split("/")[0] ?? "BTC";
  const marketPrice = markets.data?.items?.find((item) => item.symbol === base)?.price;
  const tradeOverlays = buildTradeOverlays(positions.data?.items ?? [], journal.data?.items ?? []);

  async function handleStartLive() {
    if (!confirm) {
      setConfirm(true);
      return;
    }
    setErrMsg(null);
    bot.mutate(
      { type: "start-live", confirmText },
      {
        onError: (e) => setErrMsg(e instanceof Error ? e.message : "Falha ao iniciar live"),
        onSuccess: () => {
          setConfirm(false);
          setConfirmText("");
        },
      },
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Trading Live"
        subtitle="Capital real na Binance — só após backtest, walk-forward e validação demo."
        actions={
          <div className="flex gap-2 flex-wrap">
            <Link
              to="/operacoes"
              className="rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10"
            >
              Mesa ao vivo
            </Link>
            {!botSnap.running && (
              <button
                onClick={() => bot.mutate("start")}
                disabled={bot.isPending}
                className="rounded-xl bg-gradient-to-r from-[#7C3AED] to-[#3B82F6] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Iniciar Paper (demo)
              </button>
            )}
            {isLive ? (
              <button
                onClick={() => bot.mutate("stop")}
                disabled={bot.isPending}
                className="rounded-xl bg-destructive/90 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                <StopCircle className="inline h-4 w-4 mr-1.5 -mt-0.5" />
                Parar Live
              </button>
            ) : (
              <button
                onClick={handleStartLive}
                disabled={
                  bot.isPending || !canStart || (confirm && confirmText !== "CONFIRMO LIVE")
                }
                className={`rounded-xl px-4 py-2 text-sm font-medium disabled:opacity-50 ${
                  confirm
                    ? "bg-destructive text-white animate-pulse"
                    : "bg-gradient-to-r from-[#EF4444] to-[#F59E0B] text-white"
                }`}
              >
                <Rocket className="inline h-4 w-4 mr-1.5 -mt-0.5" />
                {confirm ? "Confirmar — capital real" : "Iniciar Live"}
              </button>
            )}
          </div>
        }
      />

      {gates.requires_opt_in && !gates.checks.find((c) => c.label.startsWith("Opt-in"))?.ok && (
        <div className="rounded-xl border border-warning/40 bg-warning/10 px-4 py-3 text-sm flex gap-3 items-start">
          <AlertTriangle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
          <div>
            <div className="font-medium">Opt-in obrigatório</div>
            <div className="text-muted-foreground mt-1">
              Defina <code className="text-secondary">ATLAS_ALLOW_LIVE=1</code> no{" "}
              <code className="text-secondary">.env</code> e reinicie a API antes de operar capital
              real.
            </div>
          </div>
        </div>
      )}

      {errMsg && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {errMsg}
        </div>
      )}

      {confirm && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-4 text-sm">
          <div className="font-medium text-destructive">Confirmação obrigatória para live</div>
          <div className="mt-1 text-muted-foreground">
            Digite <code className="text-secondary">CONFIRMO LIVE</code> para liberar ordens reais.
          </div>
          <input
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            className="mt-3 w-full max-w-sm rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
            placeholder="CONFIRMO LIVE"
          />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Panel title="Status do Bot" className="lg:col-span-1">
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Modo</span>
              <span className={isLive ? "text-destructive font-medium" : ""}>
                {botSnap.mode ?? "paper"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Rodando</span>
              <span className={botSnap.running ? "text-success" : ""}>
                {botSnap.running ? "Sim" : "Não"}
              </span>
            </div>
            {botSnap.instance_count != null && botSnap.instance_count > 0 && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Instâncias</span>
                <span className="text-secondary">{botSnap.instance_count}</span>
              </div>
            )}
            {instances.length > 0 ? (
              <div className="space-y-2 pt-1 border-t border-white/5">
                <div className="text-[11px] uppercase text-muted-foreground">Engines ativos</div>
                {instances.map((inst) => (
                  <div key={inst.key} className="rounded-lg bg-white/[0.03] px-3 py-2 text-xs">
                    <div className="font-medium">{inst.strategy_label}</div>
                    <div className="text-muted-foreground mt-0.5">
                      {inst.symbol} · {inst.timeframe.toUpperCase()}
                      {inst.in_position ? " · em posição" : ""}
                      {inst.alive ? "" : " · parado"}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Estratégia</span>
                  <span>{config.strategy}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Par / TF</span>
                  <span>
                    {config.symbol} · {config.timeframe}
                  </span>
                </div>
              </>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Stop na exchange</span>
              <span>{config.use_exchange_stop ? "Sim" : "Não"}</span>
            </div>
            {botSnap.last_error && (
              <div className="rounded-lg bg-destructive/10 border border-destructive/30 p-2 text-xs text-destructive">
                {botSnap.last_error}
              </div>
            )}
          </div>
        </Panel>

        <Panel
          title="Gates de Promoção"
          className="lg:col-span-2"
          action={
            <span className={`chip ${gates.eligible ? "text-success" : "text-warning"}`}>
              {gates.checks_passed}/{gates.checks_total} ok
            </span>
          }
        >
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {gates.checks.map((c) => (
              <li
                key={c.label}
                className={`flex items-center justify-between rounded-xl border px-4 py-3 ${
                  c.ok ? "bg-success/10 border-success/30" : "bg-white/[0.02] border-white/10"
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  {c.ok ? (
                    <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
                  ) : (
                    <ShieldAlert className="h-4 w-4 text-warning shrink-0" />
                  )}
                  <span className="text-sm truncate">{c.label}</span>
                </div>
                <span className="num text-xs text-muted-foreground ml-2 shrink-0">{c.value}</span>
              </li>
            ))}
          </ul>
          {!gates.eligible && gates.blocking_reasons.length > 0 && (
            <p className="mt-4 text-xs text-muted-foreground">
              Pendências: {gates.blocking_reasons.slice(0, 4).join(" · ")}
              {gates.blocking_reasons.length > 4 ? " …" : ""}
            </p>
          )}
        </Panel>
      </div>

      {botSnap.running ? (
        <Suspense
          fallback={
            <div className="glass rounded-2xl h-[360px] grid place-items-center text-sm text-muted-foreground">
              Carregando gráfico em tempo real...
            </div>
          }
        >
          <LiveTradingViewChart
            symbol={symbol}
            timeframe={timeframe}
            price={marketPrice}
            trades={tradeOverlays}
          />
        </Suspense>
      ) : (
        <Panel
          title="Gráfico em tempo real"
          subtitle="Paper e Live usam o mesmo gráfico operacional."
        >
          <div className="rounded-xl border border-dashed border-white/15 bg-white/[0.02] px-4 py-8 text-sm text-muted-foreground text-center">
            Inicie Paper ou Live para carregar o gráfico em tempo real nesta tela.
          </div>
        </Panel>
      )}

      <Panel
        title="Mesa ao vivo"
        action={
          botSnap.running ? (
            <Link to="/operacoes" className="chip text-success hover:underline">
              tela completa
            </Link>
          ) : (
            <span className="chip text-muted-foreground">bot parado</span>
          )
        }
      >
        {feed.data ? (
          <OperationsFeed data={feed.data} compact />
        ) : (
          <p className="text-sm text-muted-foreground">
            Feed indisponível. Reinicie a API e use <strong>Iniciar Paper</strong> para ver ticks em
            tempo real na demo enquanto os gates live não passam.
          </p>
        )}
      </Panel>

      <Panel title="Fluxo recomendado">
        <ol className="text-sm text-muted-foreground space-y-2 list-decimal list-inside">
          <li>
            Backtest + walk-forward com score L1 ≥ 75 (
            <Link to="/ia" className="text-primary hover:underline">
              IA de Seleção
            </Link>
            )
          </li>
          <li>
            Paper trading na Binance Demo por pelo menos {gates.min_paper_days} dias (
            <Link to="/validacao" className="text-primary hover:underline">
              Validação Demo
            </Link>
            )
          </li>
          <li>
            Configure <code className="text-secondary">BINANCE_LIVE_*</code> e{" "}
            <code className="text-secondary">ATLAS_ALLOW_LIVE=1</code>
          </li>
          <li>Inicie live nesta tela — ordens reais com stop na exchange</li>
        </ol>
      </Panel>
    </div>
  );
}
