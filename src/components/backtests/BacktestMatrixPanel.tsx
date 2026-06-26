import { Link } from "@tanstack/react-router";
import { Fragment, useEffect, useState } from "react";
import type {
  BacktestBatchItem,
  BacktestMatrixGroup,
  BacktestMatrixResponse,
  OperatedBase,
} from "@/lib/api";
import {
  buildMatrixGroups,
  filterMatrixByAsset,
  splitMatrixByAsset,
} from "@/lib/backtest-matrix-groups";
import { formatReturn } from "@/lib/backtest-format";
import { formatBacktestPeriodShort, formatTradesWithPeriod } from "@/lib/backtest-period";
import { ApiError } from "@/lib/api";
import { TrendingDown, TrendingUp, ArrowLeftRight } from "lucide-react";
import { BacktestInlineChart } from "@/components/backtests/BacktestChartPanel";

export type BacktestMatrixSelection = {
  strategy: string;
  timeframe: string;
  base_asset: OperatedBase;
};

const ASSET_TABS: { id: OperatedBase; label: string; color: string }[] = [
  { id: "BTC", label: "BTC/USDT", color: "#F7931A" },
  { id: "ETH", label: "ETH/USDT", color: "#627EEA" },
];

const GROUP_META: Record<
  BacktestMatrixGroup["market_type"],
  { badge: string; badgeLabel: string; icon: typeof TrendingUp }
> = {
  bull: { badge: "chip text-success", badgeLabel: "Alta", icon: TrendingUp },
  bear: { badge: "chip text-destructive", badgeLabel: "Baixa", icon: TrendingDown },
  range: { badge: "chip text-warning", badgeLabel: "Lateral", icon: ArrowLeftRight },
};

function inferMarketType(strategy: string): BacktestMatrixGroup["market_type"] {
  if (
    strategy.includes("short") ||
    strategy.includes("_bear") ||
    strategy.includes("breakout_down")
  ) {
    return "bear";
  }
  if (
    strategy.startsWith("range_") ||
    strategy.startsWith("bb_squeeze") ||
    strategy.startsWith("regime_switching")
  ) {
    return "range";
  }
  return "bull";
}

export function BacktestMatrixTable({
  items,
  selected,
  onSelect,
  asset = "BTC",
}: {
  items: BacktestBatchItem[];
  selected?: BacktestMatrixSelection | null;
  onSelect?: (row: BacktestMatrixSelection | null) => void;
  asset?: OperatedBase;
}) {
  if (!items.length) {
    return <p className="text-sm text-muted-foreground">Nenhum resultado nesta categoria.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-white/10">
      <table className="w-full text-sm">
        <thead className="text-[11px] uppercase text-muted-foreground bg-white/[0.02]">
          <tr className="text-left">
            <th className="px-3 py-2">Estratégia</th>
            <th className="px-3 py-2">TF</th>
            <th className="px-3 py-2">Período simulado</th>
            <th className="px-3 py-2 text-right">Lucro / prejuízo</th>
            <th className="px-3 py-2 text-right">Score</th>
            <th className="px-3 py-2 text-right">PF</th>
            <th className="px-3 py-2 text-right">DD%</th>
            <th
              className="px-3 py-2 text-right"
              title="Operações fechadas no intervalo de candles do backtest"
            >
              Trades
            </th>
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
            const rowAsset = row.base_asset ?? asset;
            const isSelected =
              selected?.strategy === row.strategy &&
              selected?.timeframe === row.timeframe &&
              (selected?.base_asset ?? "BTC") === rowAsset;
            const rowSelection: BacktestMatrixSelection = {
              strategy: row.strategy,
              timeframe: row.timeframe,
              base_asset: rowAsset,
            };
            return (
              <Fragment key={`${rowAsset}-${row.strategy}-${row.timeframe}`}>
                <tr
                  onClick={onSelect ? () => onSelect(isSelected ? null : rowSelection) : undefined}
                  className={`border-t border-white/5 ${onSelect ? "cursor-pointer transition-colors" : ""} ${
                    isSelected
                      ? "bg-primary/10 ring-1 ring-inset ring-primary/40"
                      : onSelect
                        ? "hover:bg-white/[0.03]"
                        : ""
                  } ${noTrades ? "opacity-80" : ""}`}
                >
                  <td className="px-3 py-2">
                    {row.strategy_label}
                    {noTrades && (
                      <span className="ml-2 text-[10px] uppercase text-amber-400/80">
                        sem trades
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 uppercase">{row.timeframe}</td>
                  <td
                    className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap"
                    title={formatBacktestPeriodShort(row)}
                  >
                    {formatBacktestPeriodShort(row)}
                  </td>
                  <td className={`px-3 py-2 text-right num font-semibold ${tone}`}>
                    {noTrades ? "0% · inativo" : formatReturn(row.metrics?.total_return_pct)}
                  </td>
                  <td className="px-3 py-2 text-right num">{row.metrics?.atlas_score ?? "—"}</td>
                  <td className="px-3 py-2 text-right num">
                    {noTrades ? "—" : (row.metrics?.profit_factor ?? "—")}
                  </td>
                  <td className="px-3 py-2 text-right num">
                    {noTrades ? "—" : (row.metrics?.max_drawdown_pct ?? "—")}
                  </td>
                  <td
                    className="px-3 py-2 text-right num"
                    title={formatTradesWithPeriod(trades, row)}
                  >
                    {formatTradesWithPeriod(trades, row)}
                  </td>
                </tr>
                {isSelected && (
                  <tr>
                    <td colSpan={8} className="p-0 align-top">
                      <BacktestInlineChart selection={rowSelection} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function BacktestMatrixGroupSection({
  group,
  selected,
  onSelect,
  asset = "BTC",
}: {
  group: BacktestMatrixGroup;
  selected?: BacktestMatrixSelection | null;
  onSelect?: (row: BacktestMatrixSelection | null) => void;
  asset?: OperatedBase;
}) {
  if (!group.items.length) return null;
  const meta = GROUP_META[group.market_type];
  const Icon = meta.icon;

  return (
    <div className="space-y-3 rounded-xl border border-white/10 bg-white/[0.02] p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon
            className={`h-4 w-4 ${group.market_type === "bear" ? "text-destructive" : group.market_type === "range" ? "text-warning" : "text-success"}`}
          />
          <h3 className="text-sm font-semibold">{group.label}</h3>
          <span className={meta.badge}>{meta.badgeLabel}</span>
        </div>
        <span className="text-xs text-muted-foreground">{group.total} combinação(ões)</span>
      </div>
      {group.best_return && (
        <div
          className={`rounded-lg border p-2 text-xs ${
            group.market_type === "bear"
              ? "border-destructive/30 bg-destructive/10"
              : group.market_type === "range"
                ? "border-warning/30 bg-warning/10"
                : "border-success/30 bg-success/10"
          }`}
        >
          Melhor nesta categoria: <strong>{group.best_return.strategy_label}</strong> ·{" "}
          {group.best_return.timeframe.toUpperCase()} ·{" "}
          <span className="num">{formatReturn(group.best_return.metrics?.total_return_pct)}</span>
        </div>
      )}
      <BacktestMatrixTable
        items={group.items}
        selected={selected}
        onSelect={onSelect}
        asset={asset}
      />
    </div>
  );
}

export function BacktestMatrixGroupedSummary({
  matrix,
  selected,
  onSelect,
  assetLabel,
}: {
  matrix: BacktestMatrixResponse;
  selected?: BacktestMatrixSelection | null;
  onSelect?: (row: BacktestMatrixSelection | null) => void;
  assetLabel?: string;
}) {
  const asset = selected?.base_asset ?? matrix.items[0]?.base_asset ?? "BTC";
  const groups = buildMatrixGroups(matrix.items);

  return (
    <div className="space-y-6">
      <div className="text-sm text-muted-foreground">
        {matrix.total} combinações{assetLabel ? ` · ${assetLabel}` : ""} · separadas por mercado
        (Alta / Baixa / Lateral)
      </div>
      <p className="text-xs text-muted-foreground">
        <strong>Clique em uma linha</strong> para abrir o gráfico logo abaixo dela (clique de novo
        para fechar). Verde = trade positivo · vermelho = negativo.{" "}
        <strong>Período simulado</strong> = intervalo de candles usado no backtest (histórico
        baixado da Binance).
        <strong> Trades</strong> = operações fechadas nesse intervalo — não confundir com tempo real
        de operação.
      </p>
      {matrix.best_return && (
        <div className="rounded-xl bg-success/10 border border-success/30 p-3 text-sm">
          Maior retorno geral: <strong>{matrix.best_return.strategy_label}</strong> ·{" "}
          {matrix.best_return.timeframe.toUpperCase()} ·{" "}
          <span className="num text-success">
            {formatReturn(matrix.best_return.metrics?.total_return_pct)}
          </span>
        </div>
      )}
      {groups.map((group) => (
        <BacktestMatrixGroupSection
          key={group.market_type}
          group={group}
          selected={selected}
          onSelect={onSelect}
          asset={asset}
        />
      ))}
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

export function BacktestMatrixSummary({ matrix }: { matrix: BacktestMatrixResponse }) {
  return <BacktestMatrixGroupedSummary matrix={matrix} />;
}

export function BacktestMatrixAssetTabs({
  matrix,
  selected,
  onSelect,
  defaultAsset = "BTC",
}: {
  matrix: BacktestMatrixResponse;
  selected?: BacktestMatrixSelection | null;
  onSelect?: (row: BacktestMatrixSelection | null) => void;
  defaultAsset?: OperatedBase;
}) {
  const byAsset = splitMatrixByAsset(matrix);
  const [active, setActive] = useState<OperatedBase>(() => {
    if (byAsset.BTC.total > 0) return "BTC";
    if (byAsset.ETH.total > 0) return "ETH";
    return defaultAsset;
  });

  useEffect(() => {
    if (selected?.base_asset) setActive(selected.base_asset);
  }, [selected?.base_asset]);

  const activeMatrix = filterMatrixByAsset(matrix, active);
  const tabMeta = ASSET_TABS.find((t) => t.id === active)!;

  return (
    <div className="space-y-4">
      <div className="flex gap-1 rounded-xl bg-white/5 p-1 border border-white/10 w-fit">
        {ASSET_TABS.map((tab) => {
          const count = byAsset[tab.id].total;
          const isActive = active === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => {
                setActive(tab.id);
                if (selected?.base_asset && selected.base_asset !== tab.id) {
                  onSelect?.(null);
                }
              }}
              className={`text-sm px-4 py-2 rounded-lg transition flex items-center gap-2 ${
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-white"
              }`}
            >
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: tab.color }} />
              {tab.label}
              <span className={`text-xs num ${isActive ? "opacity-90" : "opacity-60"}`}>
                ({count})
              </span>
            </button>
          );
        })}
      </div>

      {activeMatrix.total === 0 ? (
        <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.02] px-4 py-8 text-center text-sm text-muted-foreground">
          Nenhum backtest salvo para <strong className="text-white">{tabMeta.label}</strong>. Rode
          &quot;Testar todas&quot; com esse ativo selecionado em Backtests.
        </div>
      ) : (
        <BacktestMatrixGroupedSummary
          matrix={activeMatrix}
          selected={selected}
          onSelect={onSelect}
          assetLabel={tabMeta.label}
        />
      )}
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
