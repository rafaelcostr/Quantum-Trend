import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { PageHeader, Panel } from "@/components/ui/page";
import {
  BacktestMatrixError,
  BacktestMatrixSummary,
} from "@/components/backtests/BacktestMatrixPanel";
import { useRunBacktest, useRunBacktestAll, useRunWalkforward, useSettings, useBacktestMatrix } from "@/lib/queries";
import type { BacktestOptions, BacktestAllProgress, OperationalTimeframe } from "@/lib/api";
import { ApiError } from "@/lib/api";
import { Layers, Play, GitBranch } from "lucide-react";

export const Route = createFileRoute("/backtests")({
  head: () => ({ meta: [{ title: "Backtests · Quantum-Trend" }] }),
  component: Page,
});

function Page() {
  const settings = useSettings();
  const matrix = useBacktestMatrix();
  const [batchProgress, setBatchProgress] = useState<BacktestAllProgress | null>(null);
  const backtest = useRunBacktest();
  const backtestAll = useRunBacktestAll(setBatchProgress);
  const walkforward = useRunWalkforward();
  const active = settings.data?.operational?.active;
  const [strategy, setStrategy] = useState(active?.strategy ?? "mm200_trend_v2");
  const [timeframe, setTimeframe] = useState<OperationalTimeframe>(
    (active?.timeframe as OperationalTimeframe) ?? "4h",
  );

  const opts: BacktestOptions = { strategy, timeframe, quote: "USDT" };
  const strategies = settings.data?.operational?.strategies ?? [];
  const savedMatrix = matrix.data;
  const liveBatch = backtestAll.data;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Laboratório de Backtests"
        subtitle="Teste estratégias em 1H, 4H ou 1D — offline, sem alterar saldo demo."
      />

      <Panel title="Testar todas as estratégias (1H + 4H + 1D)">
        <p className="text-sm text-muted-foreground mb-4">
          Roda <strong>11 estratégias × 3 timeframes = 33 backtests</strong>. Pode levar vários minutos
          (download de candles + simulação). Resultados ficam salvos e aparecem em{" "}
          <strong>Resultados</strong> mesmo ao trocar de página.
        </p>
        <button
          onClick={() => {
            setBatchProgress(null);
            backtestAll.mutate();
          }}
          disabled={backtestAll.isPending || backtest.isPending}
          className="inline-flex items-center gap-2 rounded-2xl bg-white/5 border border-white/10 px-6 py-3 text-sm font-semibold hover:bg-white/10 disabled:opacity-50"
        >
          <Layers className="h-5 w-5" />
          {backtestAll.isPending ? "Executando matriz 1H + 4H + 1D…" : "Testar todas · 1H, 4H e 1D"}
        </button>

        {backtestAll.isPending && batchProgress && batchProgress.total > 0 && (
          <div className="mt-3 space-y-2">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{batchProgress.current ?? "Preparando…"}</span>
              <span className="num">
                {batchProgress.completed}/{batchProgress.total}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[#7C3AED] to-[#3B82F6] transition-all duration-500"
                style={{
                  width: `${Math.min(100, Math.round((batchProgress.completed / batchProgress.total) * 100))}%`,
                }}
              />
            </div>
          </div>
        )}

        {!backtestAll.isPending && liveBatch && liveBatch.total_runs > 0 && (
          <div className="mt-4 text-sm">
            Última execução:{" "}
            <span className="num text-success">{liveBatch.completed}</span> / {liveBatch.total_runs} concluídos
          </div>
        )}

        {matrix.isLoading && !savedMatrix && (
          <p className="text-sm text-muted-foreground mt-4">Carregando matriz salva…</p>
        )}

        {savedMatrix && savedMatrix.items.length > 0 && (
          <div className="mt-4">
            <BacktestMatrixSummary matrix={savedMatrix} />
          </div>
        )}

        {!matrix.isLoading && !savedMatrix?.items.length && !backtestAll.isPending && (
          <p className="text-sm text-muted-foreground mt-4">
            Nenhuma matriz salva ainda. Clique em &quot;Testar todas&quot; para gerar os 33 relatórios.
          </p>
        )}

        {matrix.isError && !savedMatrix?.items.length && (
          <BacktestMatrixError error={matrix.error} />
        )}

        {backtestAll.isError && (
          <p className="text-destructive text-sm mt-2">
            {backtestAll.error instanceof ApiError
              ? backtestAll.error.message
              : backtestAll.error instanceof Error
                ? backtestAll.error.message
                : "Falha na matriz — confirme que a API está ativa (python -m atlas.cli api)."}
          </p>
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
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
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
              {backtest.data.strategy} · {backtest.data.timeframe?.toUpperCase()} — Atlas Score:{" "}
              <span className="num text-gradient-primary">{backtest.data.metrics.atlas_score}</span>
            </div>
            <div>
              PF: {backtest.data.metrics.profit_factor} · DD: {backtest.data.metrics.max_drawdown_pct}% · Trades:{" "}
              {backtest.data.metrics.trades}
            </div>
          </div>
        )}
        {walkforward.data && (
          <div className="rounded-xl bg-success/10 border border-success/30 p-4 text-sm text-success mt-4">
            Walk-forward salvo em <code className="text-secondary">{walkforward.data.report_path}</code>
          </div>
        )}
      </Panel>

      <div className="flex flex-wrap justify-center gap-4">
        <button
          onClick={() => backtest.mutate(opts)}
          disabled={backtest.isPending || backtestAll.isPending}
          className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-[#7C3AED] to-[#3B82F6] px-8 py-4 text-base font-semibold glow-primary disabled:opacity-50"
        >
          <Play className="h-5 w-5" /> {backtest.isPending ? "Executando…" : `Backtest ${timeframe.toUpperCase()}`}
        </button>
        <button
          onClick={() => walkforward.mutate(opts)}
          disabled={walkforward.isPending || backtestAll.isPending}
          className="inline-flex items-center gap-2 rounded-2xl bg-white/5 border border-white/10 px-8 py-4 text-base font-semibold hover:bg-white/10 disabled:opacity-50"
        >
          <GitBranch className="h-5 w-5" /> {walkforward.isPending ? "Walk-forward…" : "Walk-forward OOS"}
        </button>
      </div>
    </div>
  );
}
