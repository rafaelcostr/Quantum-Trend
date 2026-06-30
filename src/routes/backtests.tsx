import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { PageHeader, Panel } from "@/components/ui/page";
import { EmptyState, InlineError, LoadingBlock } from "@/components/ui/query-state";
import { BacktestRunningBanner } from "@/components/backtests/BacktestRunningBanner";
import {
  BacktestMatrixAssetTabs,
  BacktestMatrixError,
  type BacktestMatrixSelection,
} from "@/components/backtests/BacktestMatrixPanel";
import {
  useRunBacktest,
  useRunBacktestAll,
  useRunWalkforward,
  useSettings,
  useStrategies,
  useBacktestMatrix,
  useBacktestActiveJob,
} from "@/lib/queries";
import type {
  BacktestOptions,
  BacktestAllProgress,
  OperationalTimeframe,
  OperatedBase,
} from "@/lib/api";
import { resolveRunningAsset, resolveRunningLabel } from "@/lib/backtest-running";
import { Layers, Play, GitBranch, CircleCheck, CircleX } from "lucide-react";

export const Route = createFileRoute("/backtests")({
  head: () => ({ meta: [{ title: "Backtests · Quantum-Trend" }] }),
  component: Page,
});

const MATRIX_STRATEGY_COUNT = 15;
const MATRIX_TIMEFRAMES = 3;
const MATRIX_TOTAL = MATRIX_STRATEGY_COUNT * MATRIX_TIMEFRAMES;

function Page() {
  const settings = useSettings();
  const strategiesQuery = useStrategies();
  const matrix = useBacktestMatrix();
  const activeJob = useBacktestActiveJob();
  const [batchProgress, setBatchProgress] = useState<BacktestAllProgress | null>(null);
  const backtest = useRunBacktest();
  const backtestAll = useRunBacktestAll(setBatchProgress);
  const walkforward = useRunWalkforward();
  const active = settings.data?.operational?.active;
  const [strategy, setStrategy] = useState(active?.strategy ?? "pullback_ema20_v1");
  const [timeframe, setTimeframe] = useState<OperationalTimeframe>(
    (active?.timeframe as OperationalTimeframe) ?? "4h",
  );
  const [baseAsset, setBaseAsset] = useState<OperatedBase>("BTC");
  const [matrixSelection, setMatrixSelection] = useState<BacktestMatrixSelection | null>(null);

  const remoteRunning = activeJob.data?.active && activeJob.data.status === "running";
  const runningProgress: BacktestAllProgress | null =
    (backtestAll.isPending
      ? (batchProgress ?? (remoteRunning ? activeJob.data : null))
      : remoteRunning
        ? activeJob.data
        : null) ?? null;
  const runningAsset = resolveRunningAsset(runningProgress);
  const runningLabel = resolveRunningLabel(runningProgress);
  const isRunning = !!runningProgress && runningProgress.status === "running";

  useEffect(() => {
    if (isRunning && runningAsset) {
      setBaseAsset(runningAsset);
    }
  }, [isRunning, runningAsset]);

  useEffect(() => {
    if (backtestAll.isError) setBatchProgress(null);
  }, [backtestAll.isError]);

  const opts: BacktestOptions = { strategy, timeframe, quote: "USDT", base_asset: baseAsset };
  const strategyItems = strategiesQuery.data?.items ?? settings.data?.operational?.strategies ?? [];
  const bullItems = strategyItems.filter((s) => (s.market_type ?? s.strategy_category) === "bull");
  const bearItems = strategyItems.filter((s) => (s.market_type ?? s.strategy_category) === "bear");
  const rangeItems = strategyItems.filter(
    (s) => (s.market_type ?? s.strategy_category) === "range",
  );
  const otherItems = strategyItems.filter(
    (s) => !["bull", "bear", "range"].includes(s.market_type ?? s.strategy_category ?? ""),
  );
  const savedMatrix = matrix.data;
  const liveBatch = backtestAll.data;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Laboratório de Backtests"
        subtitle="Teste estratégias em 1H, 4H ou 1D — offline, sem alterar saldo demo. Resultados separados por Alta, Baixa e Lateral."
      />

      <Panel title="Testar todas as estratégias (1H + 4H + 1D)">
        <p className="text-sm text-muted-foreground mb-4">
          Roda{" "}
          <strong>
            {MATRIX_STRATEGY_COUNT} estratégias × {MATRIX_TIMEFRAMES} timeframes = {MATRIX_TOTAL}{" "}
            backtests
          </strong>{" "}
          (8 Alta · 3 Baixa · 4 Lateral) no ativo selecionado (BTC ou ETH). Pode levar vários
          minutos.
        </p>
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <label className="text-sm flex items-center gap-2">
            <span className="text-muted-foreground text-xs">Ativo</span>
            <select
              value={baseAsset}
              onChange={(e) => setBaseAsset(e.target.value as OperatedBase)}
              disabled={isRunning}
              className="rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-sm disabled:opacity-50"
            >
              <option value="BTC">BTC/USDT</option>
              <option value="ETH">ETH/USDT</option>
            </select>
          </label>
        </div>
        {isRunning && runningAsset && runningAsset !== baseAsset && (
          <p className="text-xs text-warning mb-3">
            Matriz de <strong>{runningLabel ?? runningAsset}</strong> em execução — aguarde terminar
            ou reinicie a API para trocar de ativo.
          </p>
        )}
        <button
          onClick={() => {
            setBatchProgress({
              status: "running",
              completed: 0,
              total: MATRIX_TOTAL,
              base_asset: baseAsset,
              quote: "USDT",
              asset_label: `${baseAsset}/USDT`,
              current: `Preparando matriz · ${baseAsset}/USDT…`,
            });
            backtestAll.mutate(baseAsset);
          }}
          disabled={isRunning || backtest.isPending}
          className="inline-flex items-center gap-2 rounded-2xl bg-white/5 border border-white/10 px-6 py-3 text-sm font-semibold hover:bg-white/10 disabled:opacity-50"
        >
          <Layers className="h-5 w-5" />
          {isRunning
            ? `Matriz ${runningLabel ?? "…"} em execução…`
            : `Testar todas · ${baseAsset}/USDT · 1H, 4H e 1D`}
        </button>

        <BacktestRunningBanner progress={runningProgress} totalFallback={MATRIX_TOTAL} />

        {!isRunning && backtestAll.isSuccess && liveBatch && liveBatch.total_runs > 0 && (
          <div className="mt-4 text-sm">
            Última execução ({liveBatch.base_asset ?? "BTC"}/USDT):{" "}
            <span className="num text-success">{liveBatch.completed}</span> / {liveBatch.total_runs}{" "}
            concluídos
          </div>
        )}

        {matrix.isLoading && !savedMatrix && <LoadingBlock label="Carregando matriz salva..." />}

        {savedMatrix && savedMatrix.items.length > 0 && (
          <div className="mt-4 space-y-6">
            <BacktestMatrixAssetTabs
              matrix={savedMatrix}
              selected={matrixSelection}
              onSelect={setMatrixSelection}
            />
          </div>
        )}

        {!matrix.isLoading && !savedMatrix?.items.length && !isRunning && (
          <div className="mt-4">
            <EmptyState
              title="Nenhuma matriz salva"
              detail={`Clique em Testar todas para gerar os ${MATRIX_TOTAL} relatórios.`}
            />
          </div>
        )}

        {matrix.isError && !savedMatrix?.items.length && (
          <BacktestMatrixError error={matrix.error} />
        )}

        {backtestAll.isError && (
          <InlineError error={backtestAll.error} title="Falha na matriz" className="mt-4" />
        )}

        {!backtestAll.isPending &&
          backtestAll.isSuccess &&
          liveBatch &&
          (liveBatch.failed ?? 0) > 0 && (
            <div className="mt-4 rounded-xl border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning space-y-2">
              <p>
                {liveBatch.completed}/{liveBatch.total_runs} concluídos · {liveBatch.failed}{" "}
                falha(s).
              </p>
              <ul className="text-xs space-y-1 list-disc pl-4">
                {(liveBatch.errors ?? []).slice(0, 6).map((e) => (
                  <li key={`${e.strategy}-${e.timeframe}`}>
                    <strong>{e.strategy}</strong> · {e.timeframe.toUpperCase()} — {e.error}
                  </li>
                ))}
              </ul>
            </div>
          )}
      </Panel>

      <Panel title="Backtest individual">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <label className="text-sm space-y-1">
            <span className="text-muted-foreground text-xs">Estratégia</span>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-sm"
            >
              {bullItems.length > 0 && (
                <optgroup label="Estratégias de Alta">
                  {bullItems.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </optgroup>
              )}
              {bearItems.length > 0 && (
                <optgroup label="Estratégias de Baixa">
                  {bearItems.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </optgroup>
              )}
              {rangeItems.length > 0 && (
                <optgroup label="Estratégias Laterais">
                  {rangeItems.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </optgroup>
              )}
              {otherItems.length > 0 && (
                <optgroup label="Outras">
                  {otherItems.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          </label>
          <label className="text-sm space-y-1">
            <span className="text-muted-foreground text-xs">Ativo</span>
            <select
              value={baseAsset}
              onChange={(e) => setBaseAsset(e.target.value as OperatedBase)}
              className="w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-sm"
            >
              <option value="BTC">BTC/USDT</option>
              <option value="ETH">ETH/USDT</option>
            </select>
          </label>
          <label className="text-sm space-y-1">
            <span className="text-muted-foreground text-xs">Gráfico</span>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value as OperationalTimeframe)}
              className="w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-sm"
            >
              <option value="1h">1 hora (1H)</option>
              <option value="4h">4 horas (4H)</option>
              <option value="1d">Diário (1D)</option>
            </select>
          </label>
        </div>
        {backtest.data && (
          <div className="rounded-xl bg-white/[0.03] border border-white/5 p-4 text-sm space-y-1">
            <div>
              {backtest.data.strategy} · {baseAsset}/USDT · {backtest.data.timeframe?.toUpperCase()}{" "}
              — Atlas Score:{" "}
              <span className="num text-gradient-primary">{backtest.data.metrics.atlas_score}</span>
            </div>
            <div>
              PF: {backtest.data.metrics.profit_factor} · DD:{" "}
              {backtest.data.metrics.max_drawdown_pct}% · Trades: {backtest.data.metrics.trades}
            </div>
          </div>
        )}
        {walkforward.data && <WalkforwardValidationSummary data={walkforward.data} />}
      </Panel>

      <div className="flex flex-wrap justify-center gap-4">
        <button
          onClick={() => backtest.mutate(opts)}
          disabled={backtest.isPending || isRunning}
          className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-[#7C3AED] to-[#3B82F6] px-8 py-4 text-base font-semibold glow-primary disabled:opacity-50"
        >
          <Play className="h-5 w-5" />{" "}
          {backtest.isPending
            ? "Executando…"
            : `Backtest ${baseAsset} · ${timeframe.toUpperCase()}`}
        </button>
        <button
          onClick={() => walkforward.mutate(opts)}
          disabled={walkforward.isPending || isRunning}
          className="inline-flex items-center gap-2 rounded-2xl bg-white/5 border border-white/10 px-8 py-4 text-base font-semibold hover:bg-white/10 disabled:opacity-50"
        >
          <GitBranch className="h-5 w-5" />{" "}
          {walkforward.isPending ? "Walk-forward…" : "Walk-forward OOS"}
        </button>
      </div>
    </div>
  );
}

function pct(value?: number | null, fraction = false): string {
  if (value == null || Number.isNaN(value)) return "—";
  const normalized = fraction ? value * 100 : value;
  return `${normalized >= 0 ? "+" : ""}${normalized.toFixed(1)}%`;
}

function WalkforwardValidationSummary({ data }: { data: import("@/lib/api").WalkforwardResponse }) {
  const robustness = data.robustness ?? {};
  const mc = data.monte_carlo ?? {};
  const holdout = data.holdout;
  const checklist = data.promotion_checklist ?? [];
  return (
    <div className="rounded-xl bg-white/[0.03] border border-white/10 p-4 text-sm mt-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="font-semibold">Validação estatística concluída</div>
          <code className="text-xs text-secondary">{data.report_path}</code>
        </div>
        <div
          className={`rounded-lg px-3 py-2 text-right ${
            robustness.approved ? "bg-success/10 text-success" : "bg-warning/10 text-warning"
          }`}
        >
          <div className="text-[11px] uppercase opacity-80">Robustez</div>
          <div className="num text-lg font-semibold">
            {typeof robustness.score === "number" ? robustness.score.toFixed(1) : "—"}
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <ValidationStat label="Holdout" value={pct(holdout?.net_profit_pct, true)} />
        <ValidationStat label="Ruína" value={pct(mc.risk_of_ruin_pct)} />
        <ValidationStat label="MC P5" value={pct(mc.return_p05_pct)} />
        <ValidationStat label="DD P95" value={pct(mc.drawdown_p95_pct)} />
      </div>
      {checklist.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {checklist.map((item) => {
            const Icon = item.ok ? CircleCheck : CircleX;
            return (
              <div
                key={`${item.stage}-${item.label}`}
                className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-xs"
              >
                <Icon className={`h-4 w-4 ${item.ok ? "text-success" : "text-warning"}`} />
                <span className="flex-1">{item.label}</span>
                <span className="num text-muted-foreground text-right">{item.value}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ValidationStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2">
      <div className="text-[11px] uppercase text-muted-foreground">{label}</div>
      <div className="num font-semibold">{value}</div>
    </div>
  );
}
