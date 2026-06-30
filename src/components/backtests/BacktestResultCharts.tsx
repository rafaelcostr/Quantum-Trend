import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Panel } from "@/components/ui/page";
import type { ResultsResponse } from "@/lib/api";

export function BacktestResultCharts({ charts }: { charts: ResultsResponse }) {
  if (charts.monthly_returns.length === 0 && charts.distribution.every((d) => d.n === 0)) {
    return <p className="text-xs text-muted-foreground mt-4">Sem dados mensais para exibir.</p>;
  }

  return (
    <>
      <div className="mt-6 h-80">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={charts.equity_curve}
            margin={{ top: 10, right: 10, bottom: 0, left: -10 }}
          >
            <defs>
              <linearGradient id="eqr" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3B82F6" stopOpacity={0.55} />
                <stop offset="100%" stopColor="#3B82F6" stopOpacity={0} />
              </linearGradient>
            </defs>
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
            <Area
              type="monotone"
              dataKey="equity"
              stroke="#60a5fa"
              strokeWidth={2.5}
              fill="url(#eqr)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <Panel
          title="Retorno Mensal"
          subtitle="Variação % da equity em cada mês calendário (ex.: Abr/24)"
        >
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={charts.monthly_returns}>
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
                  {charts.monthly_returns.map((d, i) => (
                    <Cell key={i} fill={d.r >= 0 ? "#22C55E" : "#EF4444"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Distribuição de Trades">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={charts.distribution}>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis
                  dataKey="bucket"
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
                <Bar dataKey="n" radius={[6, 6, 0, 0]} fill="#7C3AED" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>
    </>
  );
}
