import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { PageHeader, Panel } from "@/components/ui/page";
import { StatCard } from "@/components/widgets/StatCard";
import {
  BacktestMatrixAssetTabs,
  BacktestMatrixError,
  type BacktestMatrixSelection,
} from "@/components/backtests/BacktestMatrixPanel";
import { formatReturn } from "@/lib/backtest-format";
import { filterMatrixByAsset } from "@/lib/backtest-matrix-groups";
import { Wallet, Target, Gauge, Activity, TrendingUp, ShieldAlert } from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { useBacktestMatrix, useResults, useBacktestActiveJob } from "@/lib/queries";
import type { BacktestBatchItem, BacktestMetrics, ResultsResponse } from "@/lib/api";
import { formatBacktestPeriodLong } from "@/lib/backtest-period";
import { BacktestRunningBanner } from "@/components/backtests/BacktestRunningBanner";

export const Route = createFileRoute("/resultados")({
  head: () => ({ meta: [{ title: "Resultados · Quantum-Trend" }] }),
  component: Page,
});

type Selection = BacktestMatrixSelection;

function Page() {
  const matrix = useBacktestMatrix();
  const activeJob = useBacktestActiveJob();
  const [selected, setSelected] = useState<Selection | null>(null);
  const results = useResults(selected);

  const remoteRunning = activeJob.data?.active && activeJob.data.status === "running";
  const runningProgress = remoteRunning ? activeJob.data : null;

  const items = matrix.data?.items ?? [];
  const activeAsset = selected?.base_asset ?? "BTC";
  const assetItems = matrix.data ? filterMatrixByAsset(matrix.data, activeAsset).items : [];

  useEffect(() => {
    if (!matrix.data || items.length === 0) {
      setSelected(null);
      return;
    }
    if (selected) {
      const slice = filterMatrixByAsset(matrix.data, selected.base_asset);
      const still = slice.items.find(
        (i) => i.strategy === selected.strategy && i.timeframe === selected.timeframe,
      );
      if (still) return;
    }
    const btc = filterMatrixByAsset(matrix.data, "BTC");
    const eth = filterMatrixByAsset(matrix.data, "ETH");
    const pick =
      (btc.best_return && { ...btc.best_return, base_asset: "BTC" as const }) ||
      (eth.best_return && { ...eth.best_return, base_asset: "ETH" as const }) ||
      (btc.items[0] && {
        strategy: btc.items[0].strategy,
        timeframe: btc.items[0].timeframe,
        base_asset: "BTC" as const,
      }) ||
      (eth.items[0] && {
        strategy: eth.items[0].strategy,
        timeframe: eth.items[0].timeframe,
        base_asset: "ETH" as const,
      });
    if (pick) {
      setSelected({
        strategy: pick.strategy,
        timeframe: pick.timeframe,
        base_asset: pick.base_asset,
      });
    }
  }, [matrix.data, items.length, selected]);

  const selectedItem = assetItems.find(
    (i) => i.strategy === selected?.strategy && i.timeframe === selected?.timeframe,
  );

  const apiMatchesSelection =
    !!selected &&
    results.data?.strategy === selected.strategy &&
    results.data?.timeframe === selected.timeframe;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Resultados dos Backtests"
        subtitle="Clique numa linha ou use o seletor abaixo para ver lucro/prejuízo e gráficos de cada estratégia."
      />

      <BacktestRunningBanner progress={runningProgress} />

      <Panel title="Lucro / prejuízo por estratégia">
        {matrix.isLoading && items.length === 0 && (
          <p className="text-sm text-muted-foreground">Carregando matriz salva…</p>
        )}

        {matrix.isError && items.length === 0 && <BacktestMatrixError error={matrix.error} />}

        {items.length === 0 && !matrix.isLoading && !matrix.isError && (
          <div className="text-sm text-muted-foreground space-y-2">
            <p>Nenhum relatório encontrado neste navegador.</p>
            <p>
              Rode{" "}
              <Link to="/backtests" className="text-primary hover:underline">
                Testar todas · 4H e 1D
              </Link>{" "}
              em Backtests. Os resultados ficam salvos ao trocar de página.
            </p>
          </div>
        )}

        {items.length > 0 && (
          <div className="space-y-3">
            {matrix.isError && (
              <p className="text-xs text-amber-400/90">
                Mostrando cópia salva no navegador. Reinicie a API para sincronizar com{" "}
                <code className="text-secondary">data/reports/</code>.
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              Clique numa linha para ver o detalhe abaixo.
            </p>
            {matrix.data && (
              <BacktestMatrixAssetTabs
                matrix={matrix.data}
                selected={selected}
                onSelect={setSelected}
              />
            )}
          </div>
        )}
      </Panel>

      {items.length > 0 && (
        <Panel title="Detalhe da estratégia selecionada">
          <div className="mb-4 flex flex-col sm:flex-row sm:items-end gap-3">
            <label className="text-sm space-y-1 flex-1">
              <span className="text-muted-foreground text-xs">Estratégia · timeframe</span>
              <select
                value={selected ? `${selected.strategy}:${selected.timeframe}` : ""}
                onChange={(e) => {
                  const [strategy, timeframe] = e.target.value.split(":");
                  if (strategy && timeframe) {
                    setSelected({ strategy, timeframe, base_asset: activeAsset });
                  }
                }}
                className="w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-sm"
              >
                {assetItems.map((row) => (
                  <option
                    key={`${row.base_asset ?? activeAsset}-${row.strategy}-${row.timeframe}`}
                    value={`${row.strategy}:${row.timeframe}`}
                  >
                    {row.strategy_label} · {row.timeframe.toUpperCase()} ·{" "}
                    {formatReturn(row.metrics?.total_return_pct)}
                  </option>
                ))}
              </select>
            </label>
            {selectedItem && (
              <div className="rounded-xl bg-white/[0.03] border border-white/10 px-4 py-2 text-sm shrink-0">
                Resultado:{" "}
                <span
                  className={`num font-semibold ${
                    (selectedItem.metrics?.total_return_pct ?? 0) >= 0
                      ? "text-success"
                      : "text-destructive"
                  }`}
                >
                  {formatReturn(selectedItem.metrics?.total_return_pct)}
                </span>
              </div>
            )}
          </div>

          {results.isFetching && (
            <p className="text-sm text-muted-foreground mb-4">Carregando gráficos…</p>
          )}

          {selectedItem?.metrics ? (
            <DetailMetrics
              key={`${selectedItem.strategy}-${selectedItem.timeframe}`}
              title={
                results.data?.title ??
                `${selectedItem.strategy_label} · ${selectedItem.timeframe.toUpperCase()}`
              }
              metrics={selectedItem.metrics}
              period={selectedItem}
              charts={apiMatchesSelection ? results.data : undefined}
              apiStale={!!results.data && !apiMatchesSelection && !results.isFetching}
            />
          ) : (
            <p className="text-sm text-muted-foreground">
              Selecione uma estratégia na tabela acima.
            </p>
          )}
        </Panel>
      )}
    </div>
  );
}

function formatPeriod(charts?: ResultsResponse, row?: BacktestBatchItem): string | null {
  return formatBacktestPeriodLong(charts) ?? formatBacktestPeriodLong(row);
}

function formatMetric(value: number | undefined, trades: number, suffix = ""): string {
  if (trades === 0) return "—";
  if (value == null || Number.isNaN(value)) return "—";
  return `${value.toFixed(suffix === "%" ? 1 : 2)}${suffix}`;
}

function DetailMetrics({
  title,
  metrics: m,
  period,
  charts,
  apiStale,
}: {
  title: string;
  metrics: BacktestMetrics;
  period?: BacktestBatchItem;
  charts?: ResultsResponse;
  apiStale?: boolean;
}) {
  const periodLine = formatPeriod(charts, period);
  const noTrades = (m.trades ?? 0) === 0;

  return (
    <>
      <p className="text-xs text-muted-foreground mb-1">{title} — simulação histórica (backtest)</p>
      {periodLine && <p className="text-xs text-muted-foreground mb-4">{periodLine}</p>}
      {!periodLine && <div className="mb-4" />}

      {noTrades && (
        <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100/90">
          <strong>Nenhum trade fechado</strong> neste backtest ({m.trades} operações). A estratégia
          não entrou em posição no gráfico/timeframe escolhido — por isso lucro, win rate e gráficos
          ficam zerados ou vazios. Tente <strong>4H</strong> ou outra estratégia na tabela acima
          (ex.: Range Hunter v1 · 1D teve 7 trades).
        </div>
      )}

      {apiStale && (
        <p className="text-xs text-amber-400/90 mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2">
          Gráficos desatualizados — reinicie a API:{" "}
          <code className="text-secondary">python -m atlas.cli api</code>.
        </p>
      )}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard
          label="Lucro Líquido"
          value={
            noTrades
              ? "0,0%"
              : `${m.total_return_pct >= 0 ? "+" : ""}${m.total_return_pct.toFixed(1)}%`
          }
          delta={noTrades ? 0 : m.total_return_pct}
          icon={Wallet}
          accent="success"
        />
        <StatCard
          label="Win Rate"
          value={formatMetric(m.win_rate_pct, m.trades, "%")}
          delta={noTrades ? 0 : m.win_rate_pct}
          icon={Target}
          accent="success"
        />
        <StatCard
          label="Profit Factor"
          value={formatMetric(m.profit_factor, m.trades)}
          delta={noTrades ? 0 : m.profit_factor}
          icon={Gauge}
          accent="primary"
        />
        <StatCard
          label="Sharpe Ratio"
          value={formatMetric(m.sharpe, m.trades)}
          delta={noTrades ? 0 : m.sharpe}
          icon={TrendingUp}
          accent="secondary"
        />
        <StatCard
          label="Drawdown"
          value={formatMetric(m.max_drawdown_pct, m.trades, "%")}
          delta={noTrades ? 0 : -m.max_drawdown_pct}
          icon={ShieldAlert}
          accent="warning"
        />
        <StatCard
          label="Trades"
          value={String(m.trades ?? 0)}
          delta={m.trades}
          icon={Activity}
          accent="primary"
        />
      </div>
      {periodLine && (
        <p className="text-xs text-muted-foreground mt-3">
          {m.trades ?? 0} operações fechadas no período acima
          {(period?.period_days ?? charts?.period_days)
            ? ` (~${Math.round(((period?.period_days ?? charts?.period_days ?? 0) / 365.25) * 10) / 10} anos de mercado simulado)`
            : ""}
          .
        </p>
      )}

      {charts &&
        charts.monthly_returns.length === 0 &&
        charts.distribution.every((d) => d.n === 0) &&
        !noTrades && (
          <p className="text-xs text-muted-foreground mt-4">Sem dados mensais para exibir.</p>
        )}

      {charts &&
        (charts.monthly_returns.length > 0 || charts.distribution.some((d) => d.n > 0)) && (
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
                  <YAxis
                    tick={{ fill: "#64748b", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
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
                      <YAxis
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
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
                      <YAxis
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
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
        )}
    </>
  );
}
