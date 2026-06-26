import type {
  BacktestAllResponse,
  BacktestBatchItem,
  BacktestMatrixResponse,
  OperatedBase,
  OperationalTimeframe,
} from "./api";
import type { BacktestPeriodFields } from "./backtest-period";
import {
  buildMatrixGroups,
  enrichItemsWithPeriodFields,
  filterMatrixByAsset,
  splitMatrixByAsset,
} from "./backtest-matrix-groups";

const STORAGE_KEY = "quantum-trend.backtest-matrix.v4";
const RESET_FLAG_KEY = "quantum-trend.reports-reset.v1";

/** Marca que relatórios foram apagados — bloqueia fallbacks locais até nova matriz na API. */
export function markReportsReset(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(RESET_FLAG_KEY, String(Date.now()));
  } catch {
    /* private mode */
  }
}

export function clearReportsResetFlag(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(RESET_FLAG_KEY);
  } catch {
    /* private mode */
  }
}

export function isReportsResetActive(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return sessionStorage.getItem(RESET_FLAG_KEY) != null;
  } catch {
    return false;
  }
}

export function emptyMatrix(quote = "USDT"): BacktestMatrixResponse {
  return {
    total: 0,
    quote: quote.toUpperCase(),
    best_return: null,
    best_score: null,
    items: [],
  };
}

function itemKey(item: Pick<BacktestBatchItem, "strategy" | "timeframe" | "base_asset">): string {
  return `${item.base_asset ?? "BTC"}:${item.strategy}:${item.timeframe}`;
}

function hasPeriod(item: BacktestBatchItem): boolean {
  return Boolean(item.period_start && item.period_end);
}

export function normalizeMatrixResponse(matrix: BacktestMatrixResponse): BacktestMatrixResponse {
  const items = enrichItemsWithPeriodFields(matrix.items ?? [], matrix.items ?? []);
  const groups = buildMatrixGroups(items);
  const byScore = sortByScore(items);
  const byAsset = matrix.by_asset
    ? {
        BTC: normalizeAssetSlice(matrix.by_asset.BTC, items, "BTC"),
        ETH: normalizeAssetSlice(matrix.by_asset.ETH, items, "ETH"),
      }
    : undefined;

  return {
    ...matrix,
    total: items.length,
    items,
    groups,
    best_return: items[0] ?? null,
    best_score: byScore[0] ?? null,
    by_asset: byAsset,
  };
}

function normalizeAssetSlice(
  slice: Omit<BacktestMatrixResponse, "by_asset"> | undefined,
  allItems: BacktestBatchItem[],
  asset: OperatedBase,
): Omit<BacktestMatrixResponse, "by_asset"> {
  const assetItems = enrichItemsWithPeriodFields(
    sortByReturn(allItems.filter((i) => (i.base_asset ?? "BTC") === asset)),
    allItems,
  );
  if (!slice?.items?.length) {
    const byScore = sortByScore(assetItems);
    return {
      total: assetItems.length,
      quote: slice?.quote ?? "USDT",
      best_return: assetItems[0] ?? null,
      best_score: byScore[0] ?? null,
      items: assetItems,
      groups: buildMatrixGroups(assetItems),
    };
  }
  const merged = enrichItemsWithPeriodFields(slice.items, allItems);
  const sorted = sortByReturn(merged);
  const byScore = sortByScore(sorted);
  return {
    ...slice,
    total: sorted.length,
    items: sorted,
    groups: buildMatrixGroups(sorted),
    best_return: sorted[0] ?? null,
    best_score: byScore[0] ?? null,
  };
}

export async function hydrateMatrixPeriods(
  matrix: BacktestMatrixResponse,
): Promise<BacktestMatrixResponse> {
  const missing = matrix.items.filter((item) => item.ok && !hasPeriod(item));
  if (!missing.length) return normalizeMatrixResponse(matrix);

  const { api } = await import("./api");
  const updates = new Map<string, BacktestPeriodFields>();

  await Promise.all(
    missing.map(async (item) => {
      try {
        const detail = await api.results({
          strategy: item.strategy,
          timeframe: item.timeframe as OperationalTimeframe,
          base_asset: item.base_asset ?? "BTC",
        });
        if (detail.period_start && detail.period_end) {
          updates.set(itemKey(item), {
            period_start: detail.period_start,
            period_end: detail.period_end,
            period_days: detail.period_days,
          });
        }
      } catch {
        /* relatório ausente */
      }
    }),
  );

  if (!updates.size) return normalizeMatrixResponse(matrix);

  const apply = (item: BacktestBatchItem): BacktestBatchItem => {
    const patch = updates.get(itemKey(item));
    return patch ? { ...item, ...patch } : item;
  };

  return normalizeMatrixResponse({
    ...matrix,
    items: matrix.items.map(apply),
  });
}

export function isMatrixHealthy(matrix: BacktestMatrixResponse | null | undefined): boolean {
  if (!matrix?.items?.length) return false;
  if (matrix.items.length === 1) return true;
  const metricSigs = matrix.items.map((i) =>
    JSON.stringify([
      i.strategy,
      i.timeframe,
      i.base_asset ?? "BTC",
      i.metrics?.total_return_pct,
      i.metrics?.win_rate_pct,
      i.metrics?.trades,
    ]),
  );
  return new Set(metricSigs).size === matrix.items.length;
}

function sortByReturn(items: BacktestBatchItem[]) {
  return [...items].sort(
    (a, b) => (b.metrics?.total_return_pct ?? 0) - (a.metrics?.total_return_pct ?? 0),
  );
}

function sortByScore(items: BacktestBatchItem[]) {
  return [...items].sort((a, b) => (b.metrics?.atlas_score ?? 0) - (a.metrics?.atlas_score ?? 0));
}

export function mergeMatrixResponses(
  prev: BacktestMatrixResponse | null | undefined,
  incoming: BacktestMatrixResponse,
  replacedAsset: import("./api").OperatedBase,
): BacktestMatrixResponse {
  const prevParts = prev?.items?.length ? splitMatrixByAsset(prev) : null;
  const nextPart = filterMatrixByAsset(incoming, replacedAsset);
  const btc = replacedAsset === "BTC" ? nextPart : (prevParts?.BTC ?? emptyMatrix());
  const eth = replacedAsset === "ETH" ? nextPart : (prevParts?.ETH ?? emptyMatrix());
  const items = sortByReturn([...btc.items, ...eth.items]);
  const byScore = sortByScore(items);
  return normalizeMatrixResponse({
    total: items.length,
    quote: incoming.quote || prev?.quote || "USDT",
    best_return: items[0] ?? null,
    best_score: byScore[0] ?? null,
    items,
    groups: buildMatrixGroups(items),
    by_asset: { BTC: btc, ETH: eth },
  });
}

export function batchToMatrix(batch: BacktestAllResponse): BacktestMatrixResponse {
  const items = sortByReturn(batch.items.filter((i) => i.ok));
  const byScore = sortByScore(items);
  const base = (batch.base_asset ?? "BTC") as import("./api").OperatedBase;
  const slice: BacktestMatrixResponse = {
    total: items.length,
    quote: batch.quote,
    best_return: items[0] ?? null,
    best_score: byScore[0] ?? null,
    items,
    groups: batch.groups?.length ? batch.groups : buildMatrixGroups(items),
  };
  return normalizeMatrixResponse({
    ...slice,
    by_asset: { [base]: slice },
  });
}

export function loadCachedMatrix(): BacktestMatrixResponse | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as BacktestMatrixResponse;
    if (!isMatrixHealthy(parsed)) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    const hasAnyPeriod = parsed.items.some((item) => item.period_start && item.period_end);
    if (parsed.items.length > 0 && !hasAnyPeriod) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return normalizeMatrixResponse(parsed);
  } catch {
    return null;
  }
}

export function saveCachedMatrix(matrix: BacktestMatrixResponse): void {
  if (typeof window === "undefined" || !isMatrixHealthy(matrix)) return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(matrix));
  } catch {
    /* quota / private mode */
  }
}

export function clearCachedMatrix(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* private mode */
  }
}

export async function buildMatrixFromResultsFallback(): Promise<BacktestMatrixResponse | null> {
  const { api } = await import("./api");
  const settings = await api.settings();
  const strategies = settings.operational?.strategies ?? [];
  const timeframes = settings.operational?.timeframes ?? ["1h", "4h", "1d"];
  const items: BacktestBatchItem[] = [];

  for (const s of strategies) {
    for (const tf of timeframes) {
      try {
        const detail = await api.results({ strategy: s.id, timeframe: tf as OperationalTimeframe });
        items.push({
          strategy: s.id,
          strategy_label: s.name,
          timeframe: tf,
          ok: true,
          period_start: detail.period_start,
          period_end: detail.period_end,
          period_days: detail.period_days,
          metrics: detail.metrics,
          result:
            detail.metrics.total_return_pct > 0
              ? "lucro"
              : detail.metrics.total_return_pct < 0
                ? "prejuizo"
                : "empate",
        });
      } catch {
        /* relatório ausente para esta combinação */
      }
    }
  }

  if (!items.length) return null;

  if (items.length > 1) {
    const sigs = new Set(items.map((i) => JSON.stringify(i.metrics)));
    if (sigs.size === 1) return null;
    const strategies = new Set(items.map((i) => `${i.strategy}:${i.timeframe}`));
    if (strategies.size !== items.length) return null;
  }

  const matrix = batchToMatrix({
    total_runs: items.length,
    completed: items.length,
    failed: 0,
    timeframes,
    quote: "USDT",
    best: null,
    items,
    errors: [],
  });
  return isMatrixHealthy(matrix) ? matrix : null;
}
