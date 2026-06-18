import { createFileRoute } from "@tanstack/react-router";
import { PageHeader, Panel } from "@/components/ui/page";
import { StatCard } from "@/components/widgets/StatCard";
import { Wallet, PieChart, TrendingUp, Shield } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { isBrowser, usePortfolio } from "@/lib/queries";

export const Route = createFileRoute("/portfolio")({
  head: () => ({ meta: [{ title: "Portfolio · Quantum-Trend" }] }),
  component: PortfolioPage,
});

function PortfolioPage() {
  const { data, isPending, error, isError } = usePortfolio();

  if (!isBrowser || isPending) {
    return <div className="text-muted-foreground text-sm">Carregando portfolio…</div>;
  }
  if (isError || !data) {
    return <div className="text-destructive text-sm">{error instanceof Error ? error.message : "Erro ao carregar portfolio."}</div>;
  }

  const p = data.portfolio;
  const monthly = data.monthly_returns ?? [];

  return (
    <div className="space-y-8">
      <PageHeader title="Portfolio" subtitle="Capital, exposição e retorno consolidado — QuantumTrend Pro." />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Capital Total" value={`$${p.total_capital.toLocaleString()}`} icon={Wallet} accent="primary" />
        <StatCard label="Disponível" value={`$${p.available_capital.toLocaleString()}`} icon={PieChart} accent="secondary" />
        <StatCard label="Alocado" value={`$${p.allocated_capital.toLocaleString()}`} icon={TrendingUp} accent="warning" />
        <StatCard label="Exposição" value={`${p.current_exposure_pct.toFixed(1)}%`} icon={Shield} accent="success" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Panel title="Retorno Mensal">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={monthly}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="month" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#12161f", border: "1px solid rgba(255,255,255,0.08)" }} />
                <Area type="monotone" dataKey="return_pct" stroke="#7C3AED" fill="url(#pfGrad)" />
                <defs>
                  <linearGradient id="pfGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#7C3AED" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#7C3AED" stopOpacity={0} />
                  </linearGradient>
                </defs>
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Resumo de Risco">
          <div className="space-y-3 text-sm mt-2">
            <Row label="P&L diário" value={`$${p.daily_pnl.toFixed(2)}`} />
            <Row label="Retorno anualizado" value={`${p.annualized_return_pct.toFixed(1)}%`} />
            <Row label="Posições abertas" value={String(data.open_positions)} />
            <Row label="Risco por trade" value={`${data.risk.risk_per_trade_pct}%`} />
            <Row label="Stop diário" value={`${data.risk.daily_stop_pct}%`} />
            <Row label="Perdas consecutivas" value={String(data.risk.consecutive_losses)} />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-white/5 pb-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="num font-medium">{value}</span>
    </div>
  );
}
