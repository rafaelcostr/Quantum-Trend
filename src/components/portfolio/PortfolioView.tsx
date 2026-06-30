import { lazy, Suspense } from "react";
import type { PortfolioResponse } from "@/lib/api";
import { Panel } from "@/components/ui/page";
import { EmptyState, LoadingBlock } from "@/components/ui/query-state";

const PortfolioCharts = lazy(() =>
  import("./PortfolioCharts").then((module) => ({ default: module.PortfolioCharts })),
);

type Props = { data: PortfolioResponse };

export function PortfolioView({ data }: Props) {
  const p = data.portfolio;
  const equity = data.equity_curve ?? [];
  const ddCurve = data.drawdown_curve ?? [];
  const strategies = data.strategy_performance ?? [];
  const allocation = data.allocation ?? [];
  const positions = data.open_positions_detail ?? [];
  const stats = data.portfolio_stats;
  const heatmap = data.monthly_heatmap ?? [];
  const health = data.health;
  const dd = data.drawdown_summary ?? { current_pct: 0, max_pct: 0 };
  const advancedRisk = data.advanced_risk;

  const healthCls =
    health?.tone === "success"
      ? "text-success border-success/30 bg-success/10"
      : health?.tone === "warning"
        ? "text-warning border-warning/30 bg-warning/10"
        : "text-destructive border-destructive/30 bg-destructive/10";

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Cap label="Capital" value={`$${p.total_capital.toLocaleString()}`} />
        <Cap label="Disponível" value={`$${p.available_capital.toLocaleString()}`} />
        <Cap label="Alocado" value={`$${p.allocated_capital.toLocaleString()}`} />
        <Cap label="Exposição" value={`${p.current_exposure_pct.toFixed(1)}%`} />
      </div>

      {health && (
        <div
          className={`rounded-2xl border px-5 py-4 flex flex-wrap items-center justify-between gap-4 ${healthCls}`}
        >
          <div>
            <div className="text-xs uppercase tracking-widest opacity-80">
              Health Score do Portfolio
            </div>
            <div className="text-3xl font-semibold num mt-1">{health.score}/100</div>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium">Estado: {health.state}</div>
            <div className="text-xs opacity-80 mt-1">
              PF {health.components.profit_factor?.toFixed(2)} · DD{" "}
              {health.components.max_drawdown_pct?.toFixed(1)}% · WR{" "}
              {health.components.win_rate_pct?.toFixed(0)}%
            </div>
          </div>
        </div>
      )}

      <Suspense fallback={<LoadingBlock label="Preparando gráficos do portfólio..." />}>
        <PortfolioCharts
          equity={equity}
          drawdownCurve={ddCurve}
          drawdownSummary={dd}
          allocation={allocation}
        />
      </Suspense>

      {advancedRisk && <AdvancedRiskPanel risk={advancedRisk} />}

      <Panel title="Risk summary" subtitle="Indicadores consolidados">
        {stats ? (
          <div className="space-y-3 text-sm">
            <StatRow label="Win Rate" value={`${stats.win_rate_pct.toFixed(1)}%`} />
            <StatRow label="Profit Factor" value={stats.profit_factor.toFixed(2)} />
            <StatRow
              label="Retorno total"
              value={`${stats.total_return_pct >= 0 ? "+" : ""}${stats.total_return_pct.toFixed(1)}%`}
            />
            <StatRow label="Sharpe Ratio" value={stats.sharpe_ratio.toFixed(2)} />
            <StatRow label="Max DD" value={`${stats.max_drawdown_pct.toFixed(1)}%`} tone="danger" />
            <StatRow label="Trades totais" value={String(stats.total_trades)} />
            <StatRow label="P&L diário" value={`$${p.daily_pnl.toFixed(2)}`} />
          </div>
        ) : (
          <EmptyState
            title="Sem estatísticas ainda"
            detail="Os indicadores aparecem após trades."
          />
        )}
      </Panel>

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
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-muted-foreground text-xs">
                      Configure estratégias em Estratégias.
                    </td>
                  </tr>
                ) : (
                  strategies.map((s) => (
                    <tr key={s.strategy_id} className="border-t border-white/5">
                      <td className="py-2.5">
                        <div className="font-medium">{s.label}</div>
                        <div className="text-[10px] text-muted-foreground">
                          {s.timeframe}
                          {s.source === "backtest" ? " · backtest" : " · paper"}
                        </div>
                      </td>
                      <td
                        className={`py-2.5 text-right num ${s.pnl_pct >= 0 ? "text-success" : "text-destructive"}`}
                      >
                        {s.pnl_pct >= 0 ? "+" : ""}
                        {s.pnl_pct.toFixed(1)}%
                      </td>
                      <td className="py-2.5 text-right num">{s.trades}</td>
                      <td className="py-2.5 text-right num">{s.win_rate_pct.toFixed(0)}%</td>
                      <td className="py-2.5 text-right num">{s.profit_factor.toFixed(2)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
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
                <tr>
                  <td colSpan={5} className="py-8 text-center text-muted-foreground text-xs">
                    Nenhuma posição aberta no momento.
                  </td>
                </tr>
              ) : (
                positions.map((pos, i) => (
                  <tr key={i} className="border-t border-white/5">
                    <td className="py-2.5 font-medium">{pos.asset}</td>
                    <td className="py-2.5 text-muted-foreground">{pos.strategy}</td>
                    <td className="py-2.5 text-right num">${pos.entry.toLocaleString()}</td>
                    <td className="py-2.5 text-right num">${pos.current.toLocaleString()}</td>
                    <td
                      className={`py-2.5 text-right num ${pos.pnl_pct >= 0 ? "text-success" : "text-destructive"}`}
                    >
                      {pos.pnl_pct >= 0 ? "+" : ""}
                      {pos.pnl_pct.toFixed(2)}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Calendário de performance" subtitle="Retorno mensal · heatmap">
        {heatmap.length === 0 ? (
          <p className="text-sm text-muted-foreground py-6 text-center">
            Histórico mensal insuficiente — acumule equity ou trades.
          </p>
        ) : (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2">
            {heatmap.map((m) => (
              <div
                key={m.month}
                className={`rounded-xl border px-2 py-3 text-center text-xs ${
                  m.tone === "good"
                    ? "border-success/30 bg-success/15 text-success"
                    : m.tone === "bad"
                      ? "border-destructive/30 bg-destructive/15 text-destructive"
                      : "border-warning/30 bg-warning/10 text-warning"
                }`}
              >
                <div className="font-medium">{m.month}</div>
                <div className="num mt-1">
                  {m.return_pct >= 0 ? "+" : ""}
                  {m.return_pct.toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function AdvancedRiskPanel({ risk }: { risk: NonNullable<PortfolioResponse["advanced_risk"]> }) {
  const exposure = risk.exposure;
  const alerts = risk.alerts ?? [];
  return (
    <Panel title="Risco avançado" subtitle="Exposição agregada, limites e sizing">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <Cap label="Exposição USDT" value={`$${exposure.total_usdt.toLocaleString()}`} />
        <Cap label="Exposição total" value={`${exposure.total_pct.toFixed(1)}%`} />
        <Cap
          label="Risco por trade"
          value={`${risk.limits.risk_per_trade_pct?.toFixed(2) ?? "—"}%`}
        />
        <Cap
          label="Scale recomendado"
          value={`${(risk.sizing.recommended_scale * 100).toFixed(0)}%`}
        />
      </div>
      {alerts.length > 0 && (
        <div className="mb-4 rounded-xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning">
          {alerts.join(" · ")}
        </div>
      )}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <RiskBucket title="Por ativo" items={exposure.by_asset} />
        <RiskBucket title="Por direção" items={exposure.by_direction} />
        <RiskBucket title="Por timeframe" items={exposure.by_timeframe} />
      </div>
      <div className="mt-4 overflow-x-auto rounded-xl border border-white/10">
        <table className="w-full text-sm min-w-[620px]">
          <thead className="text-[10px] uppercase text-muted-foreground bg-white/[0.02]">
            <tr className="text-left">
              <th className="px-3 py-2">Estratégia</th>
              <th className="px-3 py-2">Ativo</th>
              <th className="px-3 py-2">TF</th>
              <th className="px-3 py-2 text-right">Risco/trade</th>
              <th className="px-3 py-2 text-right">Máx estratégia</th>
              <th className="px-3 py-2 text-right">Máx ativo</th>
            </tr>
          </thead>
          <tbody>
            {risk.risk_allocation.map((row) => (
              <tr
                key={`${row.strategy_id}-${row.asset}-${row.timeframe}`}
                className="border-t border-white/5"
              >
                <td className="px-3 py-2 font-medium">{row.label}</td>
                <td className="px-3 py-2">{row.asset}</td>
                <td className="px-3 py-2">{row.timeframe}</td>
                <td className="px-3 py-2 text-right num">
                  ${row.risk_budget_usdt.toLocaleString()}
                </td>
                <td className="px-3 py-2 text-right num">
                  ${row.max_strategy_risk_usdt.toLocaleString()}
                </td>
                <td className="px-3 py-2 text-right num">
                  ${row.max_asset_risk_usdt.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function RiskBucket({ title, items }: { title: string; items: Record<string, number> }) {
  const rows = Object.entries(items);
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
      <div className="text-xs uppercase text-muted-foreground mb-2">{title}</div>
      {rows.length === 0 ? (
        <p className="text-xs text-muted-foreground">Sem exposição aberta.</p>
      ) : (
        <div className="space-y-2">
          {rows.map(([key, value]) => (
            <div key={key} className="flex justify-between gap-3 text-sm">
              <span>{key}</span>
              <span className="num">${value.toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
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
      <span className={`num font-medium ${tone === "danger" ? "text-destructive" : ""}`}>
        {value}
      </span>
    </div>
  );
}
