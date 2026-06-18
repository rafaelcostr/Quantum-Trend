import type { BacktestAllResponse, BacktestBatchItem, BacktestMatrixResponse, OperationalTimeframe } from "./api";

const STORAGE_KEY = "quantum-trend.backtest-matrix.v2";
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

export function isMatrixHealthy(matrix: BacktestMatrixResponse | null | undefined): boolean {
  if (!matrix?.items?.length) return false;
  if (matrix.items.length === 1) return true;
  const metricSigs = matrix.items.map((i) =>
    JSON.stringify([
      i.strategy,
      i.timeframe,
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

export function batchToMatrix(batch: BacktestAllResponse): BacktestMatrixResponse {
  const items = sortByReturn(batch.items.filter((i) => i.ok));
  const byScore = sortByScore(items);
  return {
    total: items.length,
    quote: batch.quote,
    best_return: items[0] ?? null,
    best_score: byScore[0] ?? null,
    items,
  };
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
    return parsed;
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
