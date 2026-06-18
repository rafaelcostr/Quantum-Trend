import { Panel } from "@/components/ui/page";
import type { DashboardStats, Position, RiskResponse } from "@/lib/api";

type Props = {
  positions: Position[];
  stats: DashboardStats;
  risk?: RiskResponse;
  capital: number;
  drawdownPct?: number;
  loading?: boolean;
};

export function PositionsPnLPanel({ positions, stats, risk, capital, drawdownPct, loading }: Props) {
  const dailyPnl = risk?.settings.daily_pnl ?? stats.pnl;
  const tradesToday = risk?.settings.trades_today ?? stats.trades_today;
  const winRate = stats.win_rate_pct;

  return (
    <div className="space-y-4">
      <Panel title="Posições e P&L">
        <div className="overflow-x-auto -mx-2">
          <table className="w-full text-sm min-w-[640px]">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-wider text-muted-foreground border-b border-white/5">
                <th className="px-2 py-2 font-medium">Ativo</th>
                <th className="px-2 py-2 font-medium">Estratégia</th>
                <th className="px-2 py-2 font-medium text-right">Entrada</th>
                <th className="px-2 py-2 font-medium text-right">Atual</th>
                <th className="px-2 py-2 font-medium text-right">P&L %</th>
                <th className="px-2 py-2 font-medium text-right">P&L $</th>
                <th className="px-2 py-2 font-medium text-right">Score</th>
                <th className="px-2 py-2 font-medium">Regime</th>
                <th className="px-2 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-10 text-center text-muted-foreground text-xs">
                    Carregando posições (Binance Demo)…
                  </td>
                </tr>
              ) : positions.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-10 text-center text-muted-foreground text-xs">
                    Nenhuma posição aberta — capital disponível para novas entradas.
                  </td>
                </tr>
              ) : (
                positions.map((p, i) => {
                  const up = p.pnl >= 0;
                  return (
                    <tr key={i} className="border-t border-white/5 hover:bg-white/[0.02]">
                      <td className="px-2 py-2.5 font-medium">{p.asset}/USDT</td>
                      <td className="px-2 py-2.5 text-xs text-muted-foreground">{p.strategy}</td>
                      <td className="px-2 py-2.5 text-right num">${p.entry.toLocaleString()}</td>
                      <td className="px-2 py-2.5 text-right num">${p.current.toLocaleString()}</td>
                      <td className={`px-2 py-2.5 text-right num ${up ? "text-success" : "text-destructive"}`}>
                        {up ? "+" : ""}
                        {p.pnl_pct.toFixed(2)}%
                      </td>
                      <td className={`px-2 py-2.5 text-right num ${up ? "text-success" : "text-destructive"}`}>
                        {up ? "+" : ""}${p.pnl.toFixed(2)}
                      </td>
                      <td className="px-2 py-2.5 text-right num text-primary">{Math.round(stats.alignment_score)}</td>
                      <td className="px-2 py-2.5 text-xs">—</td>
                      <td className="px-2 py-2.5">
                        <span className="chip text-success text-[10px]">Operando</span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Resumo financeiro">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Metric label="Capital" value={`$${capital.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
          <Metric
            label="Lucro diário"
            value={`${dailyPnl >= 0 ? "+" : ""}$${Math.abs(dailyPnl).toFixed(0)}`}
            tone={dailyPnl >= 0 ? "success" : "danger"}
          />
          <Metric label="Drawdown" value={`${drawdownPct != null ? drawdownPct.toFixed(1) : "—"}%`} tone="warning" />
          <Metric label="Operações hoje" value={String(tradesToday)} />
          <Metric label="Win rate" value={`${winRate.toFixed(0)}%`} />
          <Metric label="Profit factor" value={stats.profit_factor.toFixed(2)} />
        </div>
      </Panel>
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "success" | "danger" | "warning";
}) {
  const cls =
    tone === "success" ? "text-success" : tone === "danger" ? "text-destructive" : tone === "warning" ? "text-warning" : "";
  return (
    <div className="rounded-xl bg-white/[0.03] border border-white/5 p-3">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className={`mt-1 text-lg font-semibold num ${cls}`}>{value}</div>
    </div>
  );
}
