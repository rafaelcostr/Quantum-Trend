import type {
  BacktestBatchItem,
  BacktestMatrixGroup,
  BacktestMatrixResponse,
  OperatedBase,
} from "./api";

function itemKey(item: Pick<BacktestBatchItem, "strategy" | "timeframe" | "base_asset">): string {
  return `${item.base_asset ?? "BTC"}:${item.strategy}:${item.timeframe}`;
}

function hasPeriod(item: BacktestBatchItem): boolean {
  return Boolean(item.period_start && item.period_end);
}

export function enrichItemsWithPeriodFields(
  items: BacktestBatchItem[],
  lookup: BacktestBatchItem[],
): BacktestBatchItem[] {
  const byKey = new Map(lookup.filter(hasPeriod).map((item) => [itemKey(item), item]));
  return items.map((item) => {
    if (hasPeriod(item)) return item;
    const src = byKey.get(itemKey(item));
    if (!src) return item;
    return {
      ...item,
      period_start: src.period_start,
      period_end: src.period_end,
      period_days: src.period_days,
    };
  });
}

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

export function buildMatrixGroups(items: BacktestBatchItem[]): BacktestMatrixGroup[] {
  const labels: Record<BacktestMatrixGroup["market_type"], string> = {
    bull: "Estratégias de Alta",
    bear: "Estratégias de Baixa",
    range: "Estratégias Laterais",
  };
  const buckets: Record<BacktestMatrixGroup["market_type"], BacktestBatchItem[]> = {
    bull: [],
    bear: [],
    range: [],
  };

  for (const item of items) {
    const market = item.market_type ?? inferMarketType(item.strategy);
    buckets[market].push(item);
  }

  return (["bull", "bear", "range"] as const).map((market_type) => {
    const sorted = [...buckets[market_type]].sort(
      (a, b) => (b.metrics?.total_return_pct ?? 0) - (a.metrics?.total_return_pct ?? 0),
    );
    return {
      market_type,
      label: labels[market_type],
      total: sorted.length,
      best_return: sorted[0] ?? null,
      items: sorted,
    };
  });
}

function sortByReturn(items: BacktestBatchItem[]) {
  return [...items].sort(
    (a, b) => (b.metrics?.total_return_pct ?? 0) - (a.metrics?.total_return_pct ?? 0),
  );
}

function sortByScore(items: BacktestBatchItem[]) {
  return [...items].sort((a, b) => (b.metrics?.atlas_score ?? 0) - (a.metrics?.atlas_score ?? 0));
}

export function filterMatrixByAsset(
  matrix: BacktestMatrixResponse,
  base: OperatedBase,
): BacktestMatrixResponse {
  const fromApi = matrix.by_asset?.[base];
  const items = sortByReturn(
    enrichItemsWithPeriodFields(
      (fromApi?.items ?? matrix.items).filter((item) => (item.base_asset ?? "BTC") === base),
      matrix.items,
    ),
  );
  const byScore = sortByScore(items);
  return {
    total: items.length,
    quote: matrix.quote,
    best_return: items[0] ?? null,
    best_score: byScore[0] ?? null,
    items,
    groups: buildMatrixGroups(items),
  };
}

export function splitMatrixByAsset(
  matrix: BacktestMatrixResponse,
): Record<OperatedBase, BacktestMatrixResponse> {
  return {
    BTC: filterMatrixByAsset(matrix, "BTC"),
    ETH: filterMatrixByAsset(matrix, "ETH"),
  };
}
