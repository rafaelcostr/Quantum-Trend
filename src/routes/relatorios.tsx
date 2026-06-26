import { createFileRoute } from "@tanstack/react-router";
import { PageHeader, Panel } from "@/components/ui/page";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  Line,
  LineChart,
} from "recharts";
import { Download } from "lucide-react";
import { useReports } from "@/lib/queries";

export const Route = createFileRoute("/relatorios")({
  head: () => ({ meta: [{ title: "Relatórios · Quantum-Trend" }] }),
  component: Page,
});

function Page() {
  const { data, isLoading, error } = useReports();
  if (isLoading) return <div className="text-muted-foreground text-sm">Carregando relatórios…</div>;
  if (error || !data)
    return <div className="text-destructive text-sm">Erro ao carregar relatórios.</div>;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Relatórios"
        subtitle="Relatórios consolidados do backtest Atlas."
        actions={
          <button className="inline-flex items-center gap-2 rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10">
            <Download className="h-4 w-4" /> Exportar PDF
          </button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Performance Mensal">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.monthly_returns}>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis
                  dataKey="m"
                  tick={{ fill: "#64748b", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "rgba(12,16,28,0.95)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: 12,
                  }}
                />
                <Bar dataKey="r" radius={[6, 6, 0, 0]}>
                  {data.monthly_returns.map((d, i) => (
                    <Cell key={i} fill={d.r >= 0 ? "#7C3AED" : "#EF4444"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Curva de Capital">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.equity_curve}>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis
                  dataKey="day"
                  tick={{ fill: "#64748b", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "rgba(12,16,28,0.95)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: 12,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="equity"
                  stroke="#3B82F6"
                  strokeWidth={2.5}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <Panel title="Resumo">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          {data.summary.map(([l, v, c]) => (
            <div key={l} className="rounded-xl bg-white/[0.03] border border-white/5 p-4">
              <div className="text-xs text-muted-foreground">{l}</div>
              <div className={`num text-xl mt-1 ${c}`}>{v}</div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
