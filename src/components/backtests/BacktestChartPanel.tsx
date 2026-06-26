import { Loader2 } from "lucide-react";
import { Panel } from "@/components/ui/page";
import { BacktestTradeChart } from "@/components/backtests/BacktestTradeChart";
import { useBacktestChart } from "@/lib/queries";
import type { BacktestMatrixSelection } from "@/components/backtests/BacktestMatrixPanel";

function formatPeriod(start?: string | null, end?: string | null) {
  if (!start || !end) return "—";
  return `${start.slice(0, 10)} → ${end.slice(0, 10)}`;
}

export function BacktestChartPanel({ selection }: { selection: BacktestMatrixSelection }) {
  const chart = useBacktestChart(selection);

  return (
    <Panel
      title={`Gráfico do backtest · ${selection.base_asset}/USDT`}
      subtitle="Clique em outra linha da matriz para trocar. Entradas verdes = trade positivo · vermelhas = negativo."
    >
      {chart.isPending && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-16 justify-center">
          <Loader2 className="h-4 w-4 animate-spin" />
          Carregando candles e {selection.strategy} · {selection.timeframe.toUpperCase()}…
        </div>
      )}

      {chart.isError && (
        <p className="text-sm text-destructive py-8 text-center">
          {chart.error instanceof Error ? chart.error.message : "Erro ao carregar gráfico."}
        </p>
      )}

      {chart.data && !chart.isPending && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <div>
              <span className="text-muted-foreground">Estratégia: </span>
              <strong>{chart.data.strategy_label}</strong>
              <span className="text-muted-foreground ml-2 uppercase">{chart.data.timeframe}</span>
            </div>
            <div className="text-muted-foreground text-xs">
              Período: {formatPeriod(chart.data.period_start, chart.data.period_end)}
              {chart.data.bar_count != null && ` · ${chart.data.bar_count} candles`}
            </div>
          </div>

          {chart.data.summary && (
            <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
              <span>
                Trades: <strong className="text-foreground num">{chart.data.summary.trades}</strong>
              </span>
              <span>
                Wins: <strong className="text-success num">{chart.data.summary.wins}</strong>
              </span>
              <span>
                Losses: <strong className="text-destructive num">{chart.data.summary.losses}</strong>
              </span>
              <span>
                WR: <strong className="text-foreground num">{chart.data.summary.win_rate_pct}%</strong>
              </span>
              {chart.data.summary.total_return_pct != null && (
                <span>
                  Retorno:{" "}
                  <strong
                    className={`num ${
                      chart.data.summary.total_return_pct > 0 ? "text-success" : "text-destructive"
                    }`}
                  >
                    {chart.data.summary.total_return_pct > 0 ? "+" : ""}
                    {chart.data.summary.total_return_pct}%
                  </strong>
                </span>
              )}
              {chart.data.summary.atlas_score != null && (
                <span>
                  Atlas: <strong className="text-foreground num">{chart.data.summary.atlas_score}</strong>
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
            data={chart.data}
            className="h-[560px] w-full rounded-xl border border-white/10 overflow-hidden"
          />
        </div>
      )}
    </Panel>
  );
}
