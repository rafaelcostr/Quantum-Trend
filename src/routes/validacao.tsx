import { createFileRoute, Link } from "@tanstack/react-router";
import { PageHeader, Panel } from "@/components/ui/page";
import { StatCard } from "@/components/widgets/StatCard";
import { Wallet, Target, Gauge, ShieldAlert, Activity, Calendar, Rocket } from "lucide-react";
import { motion } from "framer-motion";
import { useValidation } from "@/lib/queries";

export const Route = createFileRoute("/validacao")({
  head: () => ({ meta: [{ title: "Validação Demo · Quantum-Trend" }] }),
  component: Page,
});

function Page() {
  const { data, isLoading, isPending, error } = useValidation();
  if ((isLoading || isPending) && !data) {
    return <div className="text-muted-foreground text-sm">Carregando validação…</div>;
  }
  if (error && !data)
    return <div className="text-destructive text-sm">Erro ao carregar validação demo.</div>;
  if (!data) return null;

  const {
    score,
    stats,
    criteria,
    criteria_passed,
    criteria_total,
    spark_up,
    spark_down,
    spark_mix,
    live_gates,
  } = data;
  const circ = 2 * Math.PI * 70;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Validação Demo"
        subtitle="Critérios institucionais antes de operar capital real — dados do paper trading."
        actions={
          live_gates && (
            <Link
              to="/live"
              className="rounded-xl bg-gradient-to-r from-[#EF4444]/80 to-[#F59E0B]/80 px-4 py-2 text-sm font-medium flex items-center gap-2"
            >
              <Rocket className="h-4 w-4" />
              {live_gates.eligible
                ? "Ir para Live"
                : `Live (${live_gates.checks_passed}/${live_gates.checks_total})`}
            </Link>
          )
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-3 gap-4">
          <StatCard
            label="Lucro Acumulado"
            value={`${stats.pnl >= 0 ? "+" : ""}$${stats.pnl.toLocaleString()}`}
            delta={stats.pnl}
            icon={Wallet}
            accent="success"
            data={spark_up}
          />
          <StatCard
            label="Win Rate"
            value={`${stats.win_rate.toFixed(1)}%`}
            delta={stats.win_rate}
            icon={Target}
            accent="success"
            data={spark_up}
          />
          <StatCard
            label="Profit Factor"
            value={stats.profit_factor.toFixed(2)}
            delta={stats.profit_factor}
            icon={Gauge}
            accent="primary"
            data={spark_mix}
          />
          <StatCard
            label="Drawdown Atual"
            value={`${stats.drawdown.toFixed(1)}%`}
            delta={-stats.drawdown}
            icon={ShieldAlert}
            accent="warning"
            data={spark_down}
          />
          <StatCard
            label="Trades"
            value={String(stats.trades)}
            delta={stats.trades}
            icon={Activity}
            accent="secondary"
            data={spark_up}
          />
          <StatCard
            label="Dias em execução"
            value={String(stats.days_running)}
            delta={stats.days_running}
            icon={Calendar}
            accent="primary"
            data={spark_mix}
          />
        </div>

        <Panel title="Progresso de Aprovação">
          <div className="flex flex-col items-center">
            <div className="relative h-48 w-48">
              <svg className="absolute inset-0 -rotate-90" viewBox="0 0 160 160">
                <circle
                  cx="80"
                  cy="80"
                  r="70"
                  stroke="rgba(255,255,255,0.06)"
                  strokeWidth="10"
                  fill="none"
                />
                <motion.circle
                  cx="80"
                  cy="80"
                  r="70"
                  fill="none"
                  strokeWidth="10"
                  strokeLinecap="round"
                  stroke="url(#scoreG)"
                  initial={{ strokeDasharray: `0 ${circ}` }}
                  animate={{ strokeDasharray: `${(score / 100) * circ} ${circ}` }}
                  transition={{ duration: 1.2, ease: "easeOut" }}
                />
                <defs>
                  <linearGradient id="scoreG" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#7C3AED" />
                    <stop offset="100%" stopColor="#3B82F6" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="absolute inset-0 grid place-items-center text-center">
                <div>
                  <div className="num text-5xl text-gradient-primary">{score}</div>
                  <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
                    de 100
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-5 text-xs text-muted-foreground">
              {criteria_passed} de {criteria_total} critérios atendidos
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="Critérios de Aprovação">
        <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {criteria.map((c) => (
            <li
              key={c.label}
              className={`flex items-center justify-between rounded-xl border px-4 py-3 ${
                c.ok ? "bg-success/10 border-success/30" : "bg-warning/10 border-warning/30"
              }`}
            >
              <div className="flex items-center gap-2.5">
                <span
                  className={`h-2 w-2 rounded-full ${c.ok ? "bg-success" : "bg-warning"} animate-pulse`}
                />
                <span className="text-sm">{c.label}</span>
              </div>
              <span className="num text-sm">{c.val}</span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
