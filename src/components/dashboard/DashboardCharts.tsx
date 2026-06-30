import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Panel } from "@/components/ui/page";
import type { DashboardResponse, QuantumStatus } from "@/lib/api";

const RANGES = ["1D", "7D", "30D", "90D", "1Y"] as const;
type RangeKey = (typeof RANGES)[number];

const RANGE_POINTS: Record<RangeKey, number> = {
  "1D": 2,
  "7D": 7,
  "30D": 30,
  "90D": 90,
  "1Y": 365,
};

type Props = {
  equityCurve: DashboardResponse["equity_curve"];
  drawdownCurve: NonNullable<DashboardResponse["drawdown_curve"]>;
  radarData: DashboardResponse["radar_data"];
  quantum?: QuantumStatus;
};

function filterEquity(curve: { day: string; equity: number }[], range: RangeKey) {
  const n = RANGE_POINTS[range];
  if (curve.length <= n) return curve;
  return curve.slice(-n);
}

export function DashboardCharts({ equityCurve, drawdownCurve, radarData, quantum }: Props) {
  const [range, setRange] = useState<RangeKey>("30D");
  const equityDisplay = filterEquity(equityCurve, range);

  return (
    <>
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
              <RadarChart data={radarData}>
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
              <AreaChart data={drawdownCurve}>
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
    </>
  );
}
