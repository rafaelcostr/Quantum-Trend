import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Panel } from "@/components/ui/page";
import type { ReportsResponse } from "@/lib/api";

export function ReportsCharts({ data }: { data: ReportsResponse }) {
  return (
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
  );
}
