import {
  Area,
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Panel } from "@/components/ui/page";
import { EmptyState } from "@/components/ui/query-state";
import type { PortfolioResponse } from "@/lib/api";

const ALLOC_COLORS = ["#7C3AED", "#22C55E", "#3B82F6", "#F59E0B", "#EF4444"];

type Props = {
  equity: NonNullable<PortfolioResponse["equity_curve"]>;
  drawdownCurve: NonNullable<PortfolioResponse["drawdown_curve"]>;
  drawdownSummary: NonNullable<PortfolioResponse["drawdown_summary"]>;
  allocation: NonNullable<PortfolioResponse["allocation"]>;
};

export function PortfolioCharts({ equity, drawdownCurve, drawdownSummary, allocation }: Props) {
  const chartData = equity.map((row, i) => ({
    day: row.day,
    equity: row.equity,
    drawdown_pct: drawdownCurve[i]?.drawdown_pct ?? 0,
  }));

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-4">
      <Panel title="Curva de patrimônio" subtitle="Equity curve + overlay de drawdown">
        <div className="flex gap-6 text-xs mb-3">
          <span className="text-muted-foreground">
            DD atual:{" "}
            <span className="num text-destructive">{drawdownSummary.current_pct.toFixed(1)}%</span>
          </span>
          <span className="text-muted-foreground">
            DD máximo:{" "}
            <span className="num text-destructive">{drawdownSummary.max_pct.toFixed(1)}%</span>
          </span>
        </div>
        <div className="h-80">
          {chartData.length < 2 ? (
            <EmptyChart message="Patrimônio será plotado após ticks do bot ou trades fechados." />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="day" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                <YAxis
                  yAxisId="eq"
                  tick={{ fill: "#94a3b8", fontSize: 10 }}
                  domain={["auto", "auto"]}
                />
                <YAxis
                  yAxisId="dd"
                  orientation="right"
                  tick={{ fill: "#f87171", fontSize: 10 }}
                  domain={[0, "auto"]}
                />
                <Tooltip
                  contentStyle={{
                    background: "#12161f",
                    border: "1px solid rgba(255,255,255,0.08)",
                  }}
                />
                <Legend />
                <Area
                  yAxisId="eq"
                  type="monotone"
                  dataKey="equity"
                  name="Patrimônio"
                  stroke="#22C55E"
                  fill="url(#eqGrad)"
                  strokeWidth={2}
                />
                <Bar
                  yAxisId="dd"
                  dataKey="drawdown_pct"
                  name="Drawdown %"
                  fill="#EF4444"
                  opacity={0.45}
                  barSize={6}
                />
                <defs>
                  <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22C55E" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#22C55E" stopOpacity={0} />
                  </linearGradient>
                </defs>
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
      </Panel>

      <Panel title="Alocação por estratégia">
        <div className="h-64">
          {allocation.length === 0 ? (
            <EmptyChart message="Alocação aparece com slots ativos." />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={allocation}
                  dataKey="pct"
                  nameKey="label"
                  innerRadius={52}
                  outerRadius={80}
                  paddingAngle={3}
                >
                  {allocation.map((_, i) => (
                    <Cell key={i} fill={ALLOC_COLORS[i % ALLOC_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "#12161f",
                    border: "1px solid rgba(255,255,255,0.08)",
                  }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
        {allocation.length === 0 ? (
          <EmptyState title="Sem alocação" detail="Ative slots para preencher a distribuição." />
        ) : (
          <ul className="mt-2 space-y-1 text-xs">
            {allocation.map((a, i) => (
              <li key={a.strategy_id} className="flex justify-between">
                <span className="flex items-center gap-2">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: ALLOC_COLORS[i % ALLOC_COLORS.length] }}
                  />
                  {a.label}
                </span>
                <span className="num">{a.pct.toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="h-full flex items-center justify-center text-sm text-muted-foreground text-center px-4">
      {message}
    </div>
  );
}
