import type { PortfolioResponse } from "@/lib/api";
import { Panel } from "@/components/ui/page";
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

const ALLOC_COLORS = ["#7C3AED", "#22C55E", "#3B82F6", "#F59E0B", "#EF4444"];

type Props = { data: PortfolioResponse };

export function PortfolioView({ data }: Props) {
  const p = data.portfolio;
  const equity = data.equity_curve ?? [];
  const ddCurve = data.drawdown_curve ?? [];
  const chartData = equity.map((row, i) => ({
    day: row.day,
    equity: row.equity,
    drawdown_pct: ddCurve[i]?.drawdown_pct ?? 0,
  }));
  const strategies = data.strategy_performance ?? [];
  const allocation = data.allocation ?? [];
  const positions = data.open_positions_detail ?? [];
  const stats = data.portfolio_stats;
  const heatmap = data.monthly_heatmap ?? [];
  const health = data.health;
  const dd = data.drawdown_summary ?? { current_pct: 0, max_pct: 0 };

  const healthCls =
    health?.tone === "success" ? "text-success border-success/30 bg-success/10" :
    health?.tone === "warning" ? "text-warning border-warning/30 bg-warning/10" :
    "text-destructive border-destructive/30 bg-destructive/10";

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Cap label="Capital" value={`$${p.total_capital.toLocaleString()}`} />
        <Cap label="Disponível" value={`$${p.available_capital.toLocaleString()}`} />
        <Cap label="Alocado" value={`$${p.allocated_capital.toLocaleString()}`} />
        <Cap label="Exposição" value={`${p.current_exposure_pct.toFixed(1)}%`} />
      </div>

      {health && (
        <div className={`rounded-2xl border px-5 py-4 flex flex-wrap items-center justify-between gap-4 ${healthCls}`}>
          <div>
            <div className="text-xs uppercase tracking-widest opacity-80">Health Score do Portfolio</div>
            <div className="text-3xl font-semibold num mt-1">{health.score}/100</div>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium">Estado: {health.state}</div>
            <div className="text-xs opacity-80 mt-1">
              PF {health.components.profit_factor?.toFixed(2)} · DD {health.components.max_drawdown_pct?.toFixed(1)}% · WR{" "}
              {health.components.win_rate_pct?.toFixed(0)}%
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-4">
        <Panel title="Curva de patrimônio" subtitle="Equity curve + overlay de drawdown">
          <div className="flex gap-6 text-xs mb-3">
            <span className="text-muted-foreground">
              DD atual: <span className="num text-destructive">{dd.current_pct.toFixed(1)}%</span>
            </span>
            <span className="text-muted-foreground">
              DD máximo: <span className="num text-destructive">{dd.max_pct.toFixed(1)}%</span>
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
                  <YAxis yAxisId="eq" tick={{ fill: "#94a3b8", fontSize: 10 }} domain={["auto", "auto"]} />
                  <YAxis yAxisId="dd" orientation="right" tick={{ fill: "#f87171", fontSize: 10 }} domain={[0, "auto"]} />
                  <Tooltip contentStyle={{ background: "#12161f", border: "1px solid rgba(255,255,255,0.08)" }} />
                  <Legend />
                  <Area yAxisId="eq" type="monotone" dataKey="equity" name="Patrimônio" stroke="#22C55E" fill="url(#eqGrad)" strokeWidth={2} />
                  <Bar yAxisId="dd" dataKey="drawdown_pct" name="Drawdown %" fill="#EF4444" opacity={0.45} barSize={6} />
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

        <Panel title="Risk summary" subtitle="Indicadores consolidados">
          {stats ? (
            <div className="space-y-3 text-sm">
              <StatRow label="Win Rate" value={`${stats.win_rate_pct.toFixed(1)}%`} />
              <StatRow label="Profit Factor" value={stats.profit_factor.toFixed(2)} />
              <StatRow label="Retorno total" value={`${stats.total_return_pct >= 0 ? "+" : ""}${stats.total_return_pct.toFixed(1)}%`} />
              <StatRow label="Sharpe Ratio" value={stats.sharpe_ratio.toFixed(2)} />
              <StatRow label="Max DD" value={`${stats.max_drawdown_pct.toFixed(1)}%`} tone="danger" />
              <StatRow label="Trades totais" value={String(stats.total_trades)} />
              <StatRow label="P&L diário" value={`$${p.daily_pnl.toFixed(2)}`} />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Sem estatísticas ainda.</p>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-4">
        <Panel title="Performance por estratégia">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[520px]">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wider text-muted-foreground border-b border-white/5">
                  <th className="py-2 font-medium">Estratégia</th>
                  <th className="py-2 font-medium text-right">P&L</th>
                  <th className="py-2 font-medium text-right">Trades</th>
                  <th className="py-2 font-medium text-right">Win Rate</th>
                  <th className="py-2 font-medium text-right">PF</th>
                </tr>
              </thead>
              <tbody>
                {strategies.length === 0 ? (
                  <tr><td colSpan={5} className="py-8 text-center text-muted-foreground text-xs">Configure estratégias em Estratégias.</td></tr>
                ) : strategies.map((s) => (
                  <tr key={s.strategy_id} className="border-t border-white/5">
                    <td className="py-2.5">
                      <div className="font-medium">{s.label}</div>
                      <div className="text-[10px] text-muted-foreground">{s.timeframe}{s.source === "backtest" ? " · backtest" : " · paper"}</div>
                    </td>
                    <td className={`py-2.5 text-right num ${s.pnl_pct >= 0 ? "text-success" : "text-destructive"}`}>
                      {s.pnl_pct >= 0 ? "+" : ""}{s.pnl_pct.toFixed(1)}%
                    </td>
                    <td className="py-2.5 text-right num">{s.trades}</td>
                    <td className="py-2.5 text-right num">{s.win_rate_pct.toFixed(0)}%</td>
                    <td className="py-2.5 text-right num">{s.profit_factor.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Alocação por estratégia">
          <div className="h-64">
            {allocation.length === 0 ? (
              <EmptyChart message="Alocação aparece com slots ativos." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={allocation} dataKey="pct" nameKey="label" innerRadius={52} outerRadius={80} paddingAngle={3}>
                    {allocation.map((_, i) => (
                      <Cell key={i} fill={ALLOC_COLORS[i % ALLOC_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#12161f", border: "1px solid rgba(255,255,255,0.08)" }} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
          <ul className="mt-2 space-y-1 text-xs">
            {allocation.map((a, i) => (
              <li key={a.strategy_id} className="flex justify-between">
                <span className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ background: ALLOC_COLORS[i % ALLOC_COLORS.length] }} />
                  {a.label}
                </span>
                <span className="num">{a.pct.toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <Panel title="Posições abertas">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[560px]">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-wider text-muted-foreground border-b border-white/5">
                <th className="py-2">Ativo</th>
                <th className="py-2">Estratégia</th>
                <th className="py-2 text-right">Entrada</th>
                <th className="py-2 text-right">Atual</th>
                <th className="py-2 text-right">P&L</th>
              </tr>
            </thead>
            <tbody>
              {positions.length === 0 ? (
                <tr><td colSpan={5} className="py-8 text-center text-muted-foreground text-xs">Nenhuma posição aberta no momento.</td></tr>
              ) : positions.map((pos, i) => (
                <tr key={i} className="border-t border-white/5">
                  <td className="py-2.5 font-medium">{pos.asset}</td>
                  <td className="py-2.5 text-muted-foreground">{pos.strategy}</td>
                  <td className="py-2.5 text-right num">${pos.entry.toLocaleString()}</td>
                  <td className="py-2.5 text-right num">${pos.current.toLocaleString()}</td>
                  <td className={`py-2.5 text-right num ${pos.pnl_pct >= 0 ? "text-success" : "text-destructive"}`}>
                    {pos.pnl_pct >= 0 ? "+" : ""}{pos.pnl_pct.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Calendário de performance" subtitle="Retorno mensal · heatmap">
        {heatmap.length === 0 ? (
          <p className="text-sm text-muted-foreground py-6 text-center">Histórico mensal insuficiente — acumule equity ou trades.</p>
        ) : (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2">
            {heatmap.map((m) => (
              <div
                key={m.month}
                className={`rounded-xl border px-2 py-3 text-center text-xs ${
                  m.tone === "good" ? "border-success/30 bg-success/15 text-success" :
                  m.tone === "bad" ? "border-destructive/30 bg-destructive/15 text-destructive" :
                  "border-warning/30 bg-warning/10 text-warning"
                }`}
              >
                <div className="font-medium">{m.month}</div>
                <div className="num mt-1">{m.return_pct >= 0 ? "+" : ""}{m.return_pct.toFixed(1)}%</div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function Cap({ label, value }: { label: string; value: string }) {
  return (
    <div className="glass rounded-2xl border border-white/10 px-4 py-3">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold num mt-1">{value}</div>
    </div>
  );
}

function StatRow({ label, value, tone }: { label: string; value: string; tone?: "danger" }) {
  return (
    <div className="flex justify-between border-b border-white/5 pb-2">
      <span className="text-muted-foreground">{label}</span>
      <span className={`num font-medium ${tone === "danger" ? "text-destructive" : ""}`}>{value}</span>
    </div>
  );
}

function EmptyChart({ message }: { message: string }) {
  return <div className="h-full flex items-center justify-center text-sm text-muted-foreground text-center px-4">{message}</div>;
}
