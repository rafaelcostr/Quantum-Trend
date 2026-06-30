import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense, useEffect, useState } from "react";
import { PageHeader, Panel } from "@/components/ui/page";
import { EmptyState, LoadingBlock } from "@/components/ui/query-state";
import { StatCard } from "@/components/widgets/StatCard";
import {
  BacktestMatrixAssetTabs,
  BacktestMatrixError,
  type BacktestMatrixSelection,
} from "@/components/backtests/BacktestMatrixPanel";
import { formatReturn } from "@/lib/backtest-format";
import { filterMatrixByAsset } from "@/lib/backtest-matrix-groups";
import { Wallet, Target, Gauge, Activity, TrendingUp, ShieldAlert } from "lucide-react";
import { useBacktestMatrix, useResults, useBacktestActiveJob } from "@/lib/queries";
import type { BacktestBatchItem, BacktestMetrics, ResultsResponse } from "@/lib/api";
import { formatBacktestPeriodLong } from "@/lib/backtest-period";
import { BacktestRunningBanner } from "@/components/backtests/BacktestRunningBanner";

const BacktestResultCharts = lazy(() =>
  import("@/components/backtests/BacktestResultCharts").then((module) => ({
    default: module.BacktestResultCharts,
  })),
);

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
          <LoadingBlock label="Carregando matriz salva..." />
        )}

        {matrix.isError && items.length === 0 && <BacktestMatrixError error={matrix.error} />}

        {items.length === 0 && !matrix.isLoading && !matrix.isError && (
          <EmptyState
            title="Nenhum relatório encontrado"
            detail="Rode a matriz em Backtests para preencher esta visão."
          />
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
            <div className="mb-4">
              <LoadingBlock label="Carregando gráficos..." />
            </div>
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
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3">
        <MiniMetric label="Sortino" value={m.sortino} />
        <MiniMetric label="Calmar" value={m.calmar} />
        <MiniMetric label="Payoff" value={m.payoff_ratio} />
        <MiniMetric label="Recovery" value={m.recovery_factor} />
        <MiniMetric label="Exposição" value={m.exposure_time_pct} suffix="%" />
        <MiniMetric label="VaR 95%" value={m.var_95_pct} suffix="%" />
      </div>
      {charts && <ProfessionalAnalysis charts={charts} metrics={m} />}
      {periodLine && (
        <p className="text-xs text-muted-foreground mt-3">
          {m.trades ?? 0} operações fechadas no período acima
          {(period?.period_days ?? charts?.period_days)
            ? ` (~${Math.round(((period?.period_days ?? charts?.period_days ?? 0) / 365.25) * 10) / 10} anos de mercado simulado)`
            : ""}
          .
        </p>
      )}

      {charts && !noTrades && (
        <Suspense fallback={<LoadingBlock label="Preparando gráficos do resultado..." />}>
          <BacktestResultCharts charts={charts} />
        </Suspense>
      )}
    </>
  );
}

function MiniMetric({
  label,
  value,
  suffix = "",
}: {
  label: string;
  value?: number;
  suffix?: string;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] px-3 py-2">
      <div className="text-[11px] uppercase text-muted-foreground">{label}</div>
      <div className="num text-sm font-semibold">
        {typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(2)}${suffix}` : "—"}
      </div>
    </div>
  );
}

function ProfessionalAnalysis({
  charts,
  metrics,
}: {
  charts: ResultsResponse;
  metrics: BacktestMetrics;
}) {
  const costs = charts.costs ?? {};
  const overfit = charts.overfitting;
  const yearly = charts.period_analysis?.yearly ?? [];
  const regimes = charts.period_analysis?.by_regime ?? [];
  const flags = overfit?.flags ?? [];

  return (
    <div className="mt-4 grid grid-cols-1 xl:grid-cols-3 gap-4">
      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
        <h3 className="text-sm font-semibold mb-3">Custos reais simulados</h3>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <MiniMetric label="Taxas" value={Number(costs.total_fees ?? 0)} />
          <MiniMetric label="Slippage" value={Number(costs.slippage_rate ?? 0) * 100} suffix="%" />
          <MiniMetric label="Spread" value={Number(costs.spread_rate ?? 0) * 100} suffix="%" />
          <MiniMetric label="Turnover" value={metrics.turnover} />
        </div>
      </div>
      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
        <h3 className="text-sm font-semibold mb-3">Análise por período</h3>
        <div className="space-y-2 text-xs">
          {yearly.slice(-4).map((row) => (
            <div key={row.period} className="flex justify-between gap-3">
              <span>{row.period}</span>
              <span className={row.return_pct >= 0 ? "text-success num" : "text-destructive num"}>
                {row.return_pct >= 0 ? "+" : ""}
                {row.return_pct.toFixed(1)}%
              </span>
            </div>
          ))}
          {!yearly.length && <p className="text-muted-foreground">Sem anos suficientes.</p>}
        </div>
      </div>
      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
        <h3 className="text-sm font-semibold mb-3">Overfitting e regimes</h3>
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span>Estabilidade</span>
            <span className="num text-secondary">{metrics.stability_score?.toFixed(1) ?? "—"}</span>
          </div>
          <div className="flex justify-between">
            <span>Sensibilidade</span>
            <span>{overfit?.parameter_sensitivity ?? "unknown"}</span>
          </div>
          {regimes.slice(0, 3).map((row) => (
            <div key={row.bucket} className="flex justify-between gap-3">
              <span>{row.bucket}</span>
              <span className="num">
                {row.trades} trades · PF {row.profit_factor.toFixed(2)}
              </span>
            </div>
          ))}
          <p className={flags.length ? "text-warning" : "text-success"}>
            {flags.length ? flags.join(", ") : "Sem alerta forte de overfitting."}
          </p>
        </div>
      </div>
    </div>
  );
}
