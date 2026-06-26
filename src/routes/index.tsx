import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Wallet,
  TrendingUp,
  Brain,
  Target,
  Gauge,
  Activity,
  CheckCircle2,
  MonitorPlay,
  FlaskConical,
  Rocket,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  PolarRadiusAxis,
} from "recharts";
import { motion } from "framer-motion";
import { useState } from "react";
import { PageHeader, Panel } from "@/components/ui/page";
import { MarketRegimePanel } from "@/components/dashboard/MarketRegimePanel";
import { InstitutionalPanel } from "@/components/platform/InstitutionalPanel";
import { QuantumEntryModulesPanel } from "@/components/quantum/QuantumEntryModulesPanel";
import { StatCard } from "@/components/widgets/StatCard";
import { useBotToggle, useDashboard } from "@/lib/queries";

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

const RANGES = ["1D", "7D", "30D", "90D", "1Y"] as const;
type RangeKey = (typeof RANGES)[number];

const RANGE_POINTS: Record<RangeKey, number> = {
  "1D": 2,
  "7D": 7,
  "30D": 30,
  "90D": 90,
  "1Y": 365,
};

function filterEquity(curve: { day: string; equity: number }[], range: RangeKey) {
  const n = RANGE_POINTS[range];
  if (curve.length <= n) return curve;
  return curve.slice(-n);
}

function Dashboard() {
  const { data, isPending, error, isError } = useDashboard();
  const bot = useBotToggle();
  const [range, setRange] = useState<RangeKey>("30D");
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
  const equityDisplay = filterEquity(equity_curve, range);
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

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Panel
          className="xl:col-span-2"
          title="Equity Curve"
          action={
            <div className="flex gap-1 rounded-xl bg-white/5 p-1 border border-white/10">
              {RANGES.map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setRange(r)}
                  className={`text-xs px-3 py-1.5 rounded-lg transition ${
                    range === r
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-white"
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          }
        >
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityDisplay} margin={{ top: 10, right: 10, bottom: 0, left: -10 }}>
                <defs>
                  <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#7C3AED" stopOpacity={0.55} />
                    <stop offset="100%" stopColor="#7C3AED" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis
                  dataKey="day"
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "#0f172a",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 12,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="equity"
                  stroke="#7C3AED"
                  strokeWidth={2}
                  fill="url(#eq)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Radar de Performance">
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radar_data}>
                <PolarGrid stroke="rgba(255,255,255,0.08)" />
                <PolarAngleAxis dataKey="axis" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar dataKey="v" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.35} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Drawdown Curve">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={drawdown_curve}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="day" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    background: "#0f172a",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 12,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="drawdown_pct"
                  stroke="#EF4444"
                  fill="#EF4444"
                  fillOpacity={0.2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Histórico de Scores">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={quantum?.alignment_history ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="ts" tick={{ fill: "#94a3b8", fontSize: 10 }} hide />
                <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    background: "#0f172a",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 12,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="score"
                  stroke="#7C3AED"
                  fill="#7C3AED"
                  fillOpacity={0.25}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          {quantum?.regime_label && (
            <p className="mt-3 text-xs text-muted-foreground">
              Regime atual: <span className="text-white">{quantum.regime_label}</span>
            </p>
          )}
        </Panel>
      </div>

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
