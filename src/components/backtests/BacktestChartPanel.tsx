import { Loader2 } from "lucide-react";
import { Panel } from "@/components/ui/page";
import { BacktestTradeChart } from "@/components/backtests/BacktestTradeChart";
import { useBacktestChart } from "@/lib/queries";
import type { BacktestMatrixSelection } from "@/components/backtests/BacktestMatrixPanel";

function formatPeriod(start?: string | null, end?: string | null) {
  if (!start || !end) return "—";
  return `${start.slice(0, 10)} → ${end.slice(0, 10)}`;
}

function payloadMatchesSelection(
  payload: { strategy?: string; timeframe?: string; base?: string } | undefined,
  selection: BacktestMatrixSelection,
): boolean {
  if (!payload) return false;
  return (
    payload.strategy === selection.strategy &&
    payload.timeframe === selection.timeframe &&
    (payload.base ?? "BTC") === selection.base_asset
  );
}

function BacktestChartBody({ selection }: { selection: BacktestMatrixSelection }) {
  const chart = useBacktestChart(selection);
  const payload = chart.data;
  const matches = payloadMatchesSelection(payload, selection);
  const loading = (chart.isPending || chart.isFetching) && !matches;

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-12 justify-center">
        <Loader2 className="h-4 w-4 animate-spin" />
        Carregando {selection.strategy} · {selection.timeframe.toUpperCase()}…
      </div>
    );
  }

  if (chart.isError) {
    return (
      <p className="text-sm text-destructive py-8 text-center">
        {chart.error instanceof Error ? chart.error.message : "Erro ao carregar gráfico."}
      </p>
    );
  }

  if (!payload || !matches) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
        <div>
          <span className="text-muted-foreground">Estratégia: </span>
          <strong>{payload.strategy_label}</strong>
          <span className="text-muted-foreground ml-2 uppercase">{payload.timeframe}</span>
        </div>
        <div className="text-muted-foreground text-xs">
          Período: {formatPeriod(payload.period_start, payload.period_end)}
          {payload.bar_count != null && ` · ${payload.bar_count} candles`}
        </div>
      </div>

      {payload.summary && (
        <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
          <span>
            Trades: <strong className="text-foreground num">{payload.summary.trades}</strong>
          </span>
          <span>
            Wins: <strong className="text-success num">{payload.summary.wins}</strong>
          </span>
          <span>
            Losses: <strong className="text-destructive num">{payload.summary.losses}</strong>
          </span>
          <span>
            WR: <strong className="text-foreground num">{payload.summary.win_rate_pct}%</strong>
          </span>
          {payload.summary.total_return_pct != null && (
            <span>
              Retorno:{" "}
              <strong
                className={`num ${
                  payload.summary.total_return_pct > 0 ? "text-success" : "text-destructive"
                }`}
              >
                {payload.summary.total_return_pct > 0 ? "+" : ""}
                {payload.summary.total_return_pct}%
              </strong>
            </span>
          )}
          {payload.summary.atlas_score != null && (
            <span>
              Atlas: <strong className="text-foreground num">{payload.summary.atlas_score}</strong>
            </span>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-4 text-[11px] text-muted-foreground border border-white/5 rounded-lg px-3 py-2">
        <span className="inline-flex items-center gap-1">
          <span className="text-success">▲</span> Entrada trade vencedor
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="text-destructive">▲</span> Entrada trade perdedor
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="text-muted-foreground">●</span> Saída
        </span>
      </div>

      <BacktestTradeChart
        key={`${selection.strategy}-${selection.timeframe}-${selection.base_asset}`}
        data={payload}
        className="h-[480px] w-full rounded-xl border border-white/10 overflow-hidden bg-[rgba(5,8,16,1)]"
      />
    </div>
  );
}

/** Gráfico expandido inline abaixo da linha clicada na matriz. */
export function BacktestInlineChart({ selection }: { selection: BacktestMatrixSelection }) {
  return (
    <div className="border-t border-primary/20 bg-primary/[0.04] px-4 py-4">
      <BacktestChartBody selection={selection} />
    </div>
  );
}

export function BacktestChartPanel({ selection }: { selection: BacktestMatrixSelection }) {
  return (
    <Panel
      title={`Gráfico do backtest · ${selection.base_asset}/USDT`}
      subtitle={`${selection.strategy} · ${selection.timeframe.toUpperCase()}`}
    >
      <BacktestChartBody selection={selection} />
    </Panel>
  );
}
