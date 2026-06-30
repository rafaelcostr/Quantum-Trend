import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Gauge,
  Activity,
  Brain,
  CheckCircle2,
  FlaskConical,
  MonitorPlay,
  Rocket,
  Target,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { lazy, Suspense, useState } from "react";
import { PageHeader, Panel } from "@/components/ui/page";
import { MarketRegimePanel } from "@/components/dashboard/MarketRegimePanel";
import { InstitutionalPanel } from "@/components/platform/InstitutionalPanel";
import { QuantumEntryModulesPanel } from "@/components/quantum/QuantumEntryModulesPanel";
import { StatCard } from "@/components/widgets/StatCard";
import { useBotToggle, useDashboard } from "@/lib/queries";

const DashboardCharts = lazy(() =>
  import("@/components/dashboard/DashboardCharts").then((module) => ({
    default: module.DashboardCharts,
  })),
);

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard · Quantum-Trend" },
      {
        name: "description",
        content: "Visão geral do desempenho do bot, estratégias ativas e operações.",
      },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const { data, isPending, error, isError } = useDashboard();
  const bot = useBotToggle();
  const [botErr, setBotErr] = useState<string | null>(null);

  if (isPending && !data) {
    return (
      <div className="text-muted-foreground text-sm space-y-2 py-12 text-center">
        <p>Carregando dashboard…</p>
      </div>
    );
  }
  if (isError && !data) {
    const msg = error instanceof Error ? error.message : "Erro desconhecido";
    return (
      <div className="text-destructive text-sm space-y-2">
        <p>
          Erro ao carregar dashboard. Confirme que a API Python está ativa (
          <code className="text-secondary">python -m atlas.cli api</code>) e reinicie a UI (
          <code className="text-secondary">npm.cmd run dev</code>).
        </p>
        <p className="text-xs text-muted-foreground">{msg.slice(0, 200)}</p>
      </div>
    );
  }
  if (!data) return null;

  const {
    stats,
    equity_curve,
    drawdown_curve = [],
    radar_data,
    positions,
    flow,
    spark_up,
    spark_down,
    spark_mix,
    account,
    quantum,
    market_regime,
    platform,
  } = data;
  const isLive = stats.bot_mode === "live" && stats.bot_running;
  const phaseLabel = stats.bot_phase.charAt(0).toUpperCase() + stats.bot_phase.slice(1);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        subtitle={
          <>
            {stats.balance_source === "binance_live"
              ? `Saldo real ${stats.account_label} · ${stats.active_strategy}`
              : stats.balance_source === "binance_demo"
                ? `Saldo ${stats.account_label} · ${stats.active_strategy}`
                : "Configure BINANCE_DEMO_API_* no .env"}
            <span className="ml-2 inline-flex rounded-lg bg-white/5 border border-white/10 px-2 py-0.5 text-[11px] uppercase tracking-wide">
              {phaseLabel}
            </span>
          </>
        }
        actions={
          <div className="flex gap-2 flex-wrap">
            <Link
              to="/estrategias-alta"
              className="rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10 transition"
            >
              Estratégias de Alta
            </Link>
            <Link
              to="/estrategias-baixa"
              className="rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10 transition"
            >
              Estratégias de Baixa
            </Link>
            <Link
              to="/estrategias-lateral"
              className="rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10 transition"
            >
              Estratégias Laterais
            </Link>
            <Link
              to="/live"
              className="rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10 transition"
            >
              Trading Live
            </Link>
            <button
              onClick={() => {
                setBotErr(null);
                bot.mutate(stats.bot_running ? "stop" : "start", {
                  onError: (e) =>
                    setBotErr(e instanceof Error ? e.message : "Falha ao controlar o bot"),
                });
              }}
              disabled={bot.isPending || stats.kill_switch}
              className={`rounded-xl px-4 py-2 text-sm font-medium disabled:opacity-50 ${
                isLive
                  ? "bg-destructive/90 text-white"
                  : "bg-gradient-to-r from-[#7C3AED] to-[#3B82F6] glow-primary"
              }`}
            >
              {stats.kill_switch
                ? "Kill Switch"
                : stats.bot_running
                  ? isLive
                    ? "Parar Live"
                    : "Parar Bot"
                  : "Iniciar Paper"}
            </button>
          </div>
        }
      />

      {botErr && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {botErr.slice(0, 240)}
        </div>
      )}

      {stats.kill_switch && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          Kill switch ativo — bot bloqueado. Desative em Configurações.
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-4">
        <StatCard
          label="Saldo Total"
          value={`$${stats.balance.toLocaleString()}`}
          delta={stats.balance_delta_pct}
          icon={Wallet}
          accent="primary"
          data={spark_up}
        />
        <StatCard
          label="Lucro / Prejuízo"
          value={`${stats.pnl >= 0 ? "+" : ""}$${stats.pnl.toLocaleString()}`}
          delta={stats.pnl_delta_pct}
          icon={TrendingUp}
          accent="success"
          data={spark_up}
        />
        <StatCard
          label="Estratégia Ativa"
          value={stats.active_strategy.split(" ")[0]}
          icon={Brain}
          accent="secondary"
          data={spark_mix}
        />
        <StatCard
          label="Alignment Score"
          value={`${stats.alignment_score.toFixed(0)}`}
          icon={Gauge}
          accent="primary"
          data={spark_mix}
        />
        <StatCard
          label="Health Score"
          value={`${stats.health_score.toFixed(0)}`}
          icon={Target}
          accent="warning"
          data={spark_up}
        />
        <StatCard
          label="Win Rate"
          value={`${stats.win_rate_pct.toFixed(1)}%`}
          icon={CheckCircle2}
          accent="success"
          data={spark_mix}
        />
        <StatCard
          label="Profit Factor"
          value={stats.profit_factor.toFixed(2)}
          icon={Gauge}
          accent="warning"
          data={spark_up}
        />
        <StatCard
          label="Posições Abertas"
          value={String(stats.open_positions)}
          icon={Activity}
          accent="destructive"
          data={spark_down}
        />
      </div>

      <MarketRegimePanel regime={market_regime} />
      <InstitutionalPanel platform={platform} />
      <QuantumEntryModulesPanel quantum={quantum} />

      <Suspense
        fallback={
          <Panel title="Gráficos">
            <div className="h-80 animate-pulse rounded-xl bg-white/[0.03]" />
          </Panel>
        }
      >
        <DashboardCharts
          equityCurve={equity_curve}
          drawdownCurve={drawdown_curve}
          radarData={radar_data}
          quantum={quantum}
        />
      </Suspense>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Fluxo Backtest → Live">
          <div className="space-y-3">
            {flow.map((step) => (
              <div key={step.label} className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex justify-between text-sm mb-1">
                    <span>{step.label}</span>
                    <span className="text-muted-foreground text-xs">{step.status}</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${step.pct}%`, background: step.color }}
                    />
                  </div>
                </div>
                {step.pct >= 100 ? (
                  <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
                ) : null}
              </div>
            ))}
          </div>
          <div className="mt-4 flex gap-2 flex-wrap">
            <Link
              to="/backtests"
              className="text-xs text-secondary hover:underline inline-flex items-center gap-1"
            >
              <FlaskConical className="h-3 w-3" /> Backtests
            </Link>
            <Link
              to="/validacao"
              className="text-xs text-secondary hover:underline inline-flex items-center gap-1"
            >
              <MonitorPlay className="h-3 w-3" /> Validação
            </Link>
            <Link
              to="/live"
              className="text-xs text-secondary hover:underline inline-flex items-center gap-1"
            >
              <Rocket className="h-3 w-3" /> Live
            </Link>
          </div>
        </Panel>

        <Panel title="Posições">
          {positions.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sem posição aberta.</p>
          ) : (
            positions.map((p, i) => (
              <div
                key={i}
                className="flex justify-between border-t border-white/5 first:border-t-0 py-3"
              >
                <div>
                  <span className="font-medium">{p.asset}</span>
                  <span className="chip ml-2 text-xs">{p.side}</span>
                  <div className="text-[11px] text-muted-foreground">{p.strategy}</div>
                </div>
                <div
                  className={`text-right num ${p.pnl >= 0 ? "text-success" : "text-destructive"}`}
                >
                  {p.pnl >= 0 ? "+" : ""}${p.pnl.toFixed(2)}
                </div>
              </div>
            ))
          )}
        </Panel>
      </div>
    </div>
  );
}
