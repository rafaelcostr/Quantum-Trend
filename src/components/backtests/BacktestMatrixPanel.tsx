import { Link } from "@tanstack/react-router";
import type { BacktestBatchItem, BacktestMatrixResponse } from "@/lib/api";
import { ApiError } from "@/lib/api";

export function formatReturn(value: number | undefined) {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function BacktestMatrixTable({
  items,
  selected,
  onSelect,
}: {
  items: BacktestBatchItem[];
  selected?: { strategy: string; timeframe: string } | null;
  onSelect?: (row: { strategy: string; timeframe: string }) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-white/10">
      <table className="w-full text-sm">
        <thead className="text-[11px] uppercase text-muted-foreground bg-white/[0.02]">
          <tr className="text-left">
            <th className="px-3 py-2">Estratégia</th>
            <th className="px-3 py-2">TF</th>
            <th className="px-3 py-2 text-right">Lucro / prejuízo</th>
            <th className="px-3 py-2 text-right">Score</th>
            <th className="px-3 py-2 text-right">PF</th>
            <th className="px-3 py-2 text-right">DD%</th>
            <th className="px-3 py-2 text-right">Trades</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => {
            const ret = row.metrics?.total_return_pct ?? 0;
            const trades = row.metrics?.trades ?? 0;
            const noTrades = trades === 0;
            const tone = noTrades
              ? "text-muted-foreground"
              : ret > 0
                ? "text-success"
                : ret < 0
                  ? "text-destructive"
                  : "text-muted-foreground";
            const isSelected =
              selected?.strategy === row.strategy && selected?.timeframe === row.timeframe;
            return (
              <tr
                key={`${row.strategy}-${row.timeframe}`}
                onClick={onSelect ? () => onSelect({ strategy: row.strategy, timeframe: row.timeframe }) : undefined}
                className={`border-t border-white/5 ${onSelect ? "cursor-pointer transition-colors" : ""} ${
                  isSelected ? "bg-primary/10 ring-1 ring-inset ring-primary/40" : onSelect ? "hover:bg-white/[0.03]" : ""
                } ${noTrades ? "opacity-80" : ""}`}
              >
                <td className="px-3 py-2">
                  {row.strategy_label}
                  {noTrades && (
                    <span className="ml-2 text-[10px] uppercase text-amber-400/80">sem trades</span>
                  )}
                </td>
                <td className="px-3 py-2 uppercase">{row.timeframe}</td>
                <td className={`px-3 py-2 text-right num font-semibold ${tone}`}>
                  {noTrades ? "0% · inativo" : formatReturn(row.metrics?.total_return_pct)}
                </td>
                <td className="px-3 py-2 text-right num">{row.metrics?.atlas_score ?? "—"}</td>
                <td className="px-3 py-2 text-right num">{noTrades ? "—" : (row.metrics?.profit_factor ?? "—")}</td>
                <td className="px-3 py-2 text-right num">{noTrades ? "—" : (row.metrics?.max_drawdown_pct ?? "—")}</td>
                <td className="px-3 py-2 text-right num">{trades}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function BacktestMatrixSummary({ matrix }: { matrix: BacktestMatrixResponse }) {
  return (
    <div className="space-y-3">
      <div className="text-sm text-muted-foreground">
        {matrix.total} combinações salvas · última matriz disponível offline neste navegador
      </div>
      {matrix.best_return && (
        <div className="rounded-xl bg-success/10 border border-success/30 p-3 text-sm">
          Maior retorno: <strong>{matrix.best_return.strategy_label}</strong> ·{" "}
          {matrix.best_return.timeframe.toUpperCase()} ·{" "}
          <span className="num text-success">{formatReturn(matrix.best_return.metrics?.total_return_pct)}</span>
        </div>
      )}
      <BacktestMatrixTable items={matrix.items} />
      <p className="text-xs text-muted-foreground">
        Ver detalhe e gráficos em{" "}
        <Link to="/resultados" className="text-primary hover:underline">
          Resultados
        </Link>
        . Dados em <code className="text-secondary">data/reports/</code>.
      </p>
    </div>
  );
}

export function BacktestMatrixError({ error }: { error: unknown }) {
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : "Erro ao carregar matriz.";
  return (
    <p className="text-destructive text-sm mt-2">
      {message}
      {message.includes("matrix") && (
        <span className="block text-xs text-muted-foreground mt-1">
          Depois de reiniciar a API, rode &quot;Testar todas&quot; uma vez ou recarregue a página.
        </span>
      )}
    </p>
  );
}
