import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type BacktestAllProgress, type BacktestMatrixResponse, type OperationsFeedResponse } from "./api";
import { ApiError } from "./api";
import {
  batchToMatrix,
  clearCachedMatrix,
  clearReportsResetFlag,
  emptyMatrix,
  isMatrixHealthy,
  isReportsResetActive,
  loadCachedMatrix,
  markReportsReset,
  mergeMatrixResponses,
  normalizeMatrixResponse,
  saveCachedMatrix,
} from "./backtest-matrix-store";

/** TanStack Start faz SSR — queries de API só no browser (proxy /atlas-api). */
export const isBrowser = typeof window !== "undefined";

export const queryKeys = {
  dashboard: ["dashboard"] as const,
  markets: ["markets"] as const,
  marketChart: (base: string, timeframe: string) => ["markets", "chart", base, timeframe] as const,
  positions: ["positions"] as const,
  strategies: ["strategies"] as const,
  journal: ["journal"] as const,
  intelligence: ["intelligence"] as const,
  intelligenceAnalysis: ["intelligence", "analysis"] as const,
  bot: ["bot"] as const,
  live: ["live"] as const,
  operations: ["operations"] as const,
  validation: ["validation"] as const,
  risk: ["risk"] as const,
  results: ["results"] as const,
  backtestMatrix: ["backtest", "matrix"] as const,
  backtestChart: (strategy: string, timeframe: string, base: string) =>
    ["backtest", "chart", strategy, timeframe, base] as const,
  backtestActive: ["backtest", "active"] as const,
  reports: ["reports"] as const,
  portfolio: ["portfolio"] as const,
  quantum: ["quantum"] as const,
  settings: ["settings"] as const,
  platform: ["platform"] as const,
};

export function usePortfolio() {
  return useQuery({
    queryKey: queryKeys.portfolio,
    queryFn: api.portfolio,
    enabled: isBrowser,
    staleTime: 45_000,
    refetchInterval: 90_000,
    retry: 1,
    placeholderData: (prev) => prev,
  });
}

export function useDashboard() {
  return useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: api.dashboard,
    enabled: isBrowser,
    staleTime: 45_000,
    retry: 1,
    refetchInterval: 90_000,
    placeholderData: (prev) => prev,
  });
}

export function useMarkets() {
  return useQuery({
    queryKey: queryKeys.markets,
    queryFn: api.markets,
    enabled: isBrowser,
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: 1,
    placeholderData: (prev) => prev,
  });
}

export function useMarketChart(base: string, timeframe: string, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.marketChart(base, timeframe),
    queryFn: () => api.marketChart(base, timeframe),
    enabled: isBrowser && enabled && !!base && !!timeframe,
    staleTime: 90_000,
    retry: 1,
  });
}

export function useBacktestChart(
  selection: { strategy: string; timeframe: string; base_asset: string } | null,
) {
  return useQuery({
    queryKey: selection
      ? queryKeys.backtestChart(selection.strategy, selection.timeframe, selection.base_asset)
      : ["backtest", "chart", "none"],
    queryFn: () =>
      api.backtestChart(selection!.strategy, selection!.timeframe, selection!.base_asset),
    enabled: isBrowser && !!selection?.strategy && !!selection?.timeframe,
    staleTime: 120_000,
    retry: 1,
  });
}

export function usePositions() {
  return useQuery({
    queryKey: queryKeys.positions,
    queryFn: api.positions,
    enabled: isBrowser,
    refetchInterval: 30_000,
    staleTime: 20_000,
    retry: 1,
  });
}

export function useStrategies() {
  return useQuery({ queryKey: queryKeys.strategies, queryFn: api.strategies, enabled: isBrowser, retry: 1 });
}

export function useJournal() {
  return useQuery({
    queryKey: queryKeys.journal,
    queryFn: api.journal,
    enabled: isBrowser,
    staleTime: 20_000,
    retry: 1,
    placeholderData: (prev) => prev,
  });
}

export function useIntelligence() {
  return useQuery({
    queryKey: queryKeys.intelligence,
    queryFn: api.intelligence,
    enabled: isBrowser,
    staleTime: 120_000,
    retry: 1,
    placeholderData: (prev) => prev,
  });
}

export function useIntelligenceAnalysis(enabled = true) {
  return useQuery({
    queryKey: queryKeys.intelligenceAnalysis,
    queryFn: () => api.intelligenceAnalysis(),
    enabled: isBrowser && enabled,
    staleTime: 120_000,
    retry: 1,
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"] as const,
    queryFn: api.health,
    enabled: isBrowser,
    refetchInterval: 15_000,
    retry: 1,
    staleTime: 10_000,
  });
}

export function useBotStatus() {
  return useQuery({
    queryKey: queryKeys.bot,
    queryFn: api.botStatus,
    enabled: isBrowser,
    refetchInterval: 5_000,
    retry: 1,
  });
}

export function useBotToggle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (action: "start" | "stop" | "start-live") => {
      if (action === "start") return api.botStart();
      if (action === "start-live") return api.botStartLive();
      return api.botStop();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.bot });
      qc.invalidateQueries({ queryKey: queryKeys.live });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard });
      qc.invalidateQueries({ queryKey: queryKeys.validation });
      qc.invalidateQueries({ queryKey: queryKeys.positions });
      qc.invalidateQueries({ queryKey: queryKeys.journal });
      qc.invalidateQueries({ queryKey: queryKeys.settings });
      qc.invalidateQueries({ queryKey: queryKeys.operations });
    },
  });
}

export function useLive() {
  return useQuery({
    queryKey: queryKeys.live,
    queryFn: api.live,
    enabled: isBrowser,
    staleTime: 45_000,
    refetchInterval: 60_000,
    retry: 1,
    placeholderData: (prev) => prev,
  });
}

export function useLiveGates() {
  return useQuery({ queryKey: [...queryKeys.live, "gates"], queryFn: api.liveGates, refetchInterval: 15_000 });
}

export function useOperationsFeed() {
  const bot = useBotStatus();
  const running = bot.data?.running ?? false;
  const [streamData, setStreamData] = useState<OperationsFeedResponse | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const base = import.meta.env.VITE_API_URL
      ? import.meta.env.VITE_API_URL.replace(/\/$/, "")
      : import.meta.env.DEV
        ? "/atlas-api"
        : "/api";
    const url = `${base}/operations/stream`;
    const es = new EventSource(url);
    es.onmessage = (ev) => {
      try {
        setStreamData(JSON.parse(ev.data) as OperationsFeedResponse);
      } catch {
        /* ignore malformed */
      }
    };
    es.onerror = () => setStreamData(null);
    return () => es.close();
  }, []);

  const poll = useQuery({
    queryKey: queryKeys.operations,
    queryFn: () => api.operationsFeed(),
    refetchInterval: running && !streamData ? 3_000 : 15_000,
    staleTime: 1_000,
  });

  return {
    ...poll,
    data: streamData ?? poll.data,
    isStreaming: streamData != null,
  };
}

export function useRunBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (opts?: import("./api").BacktestOptions) => api.backtest(opts ?? {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.strategies });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard });
      qc.invalidateQueries({ queryKey: queryKeys.intelligence });
      qc.invalidateQueries({ queryKey: queryKeys.results });
      qc.invalidateQueries({ queryKey: queryKeys.backtestMatrix });
      qc.invalidateQueries({ queryKey: queryKeys.reports });
      qc.invalidateQueries({ queryKey: queryKeys.live });
      qc.invalidateQueries({ queryKey: queryKeys.settings });
    },
  });
}

export function useRunBacktestAll(onProgress?: (progress: BacktestAllProgress) => void) {
  const qc = useQueryClient();
  const progressRef = useRef(onProgress);
  progressRef.current = onProgress;

  return useMutation({
    mutationFn: (baseAsset: import("./api").OperatedBase = "BTC") =>
      api.backtestAll("USDT", baseAsset, (p) => progressRef.current?.(p)),
    onSuccess: (data, baseAsset) => {
      const incoming = batchToMatrix(data);
      const prev = qc.getQueryData<BacktestMatrixResponse>(queryKeys.backtestMatrix) ?? loadCachedMatrix();
      const matrix =
        incoming.items.length > 0 && isMatrixHealthy(incoming)
          ? mergeMatrixResponses(prev, incoming, baseAsset)
          : prev;
      if (matrix && matrix.items.length > 0 && isMatrixHealthy(matrix)) {
        saveCachedMatrix(matrix);
        qc.setQueryData(queryKeys.backtestMatrix, matrix);
      }
      qc.invalidateQueries({ queryKey: queryKeys.strategies });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard });
      qc.invalidateQueries({ queryKey: queryKeys.intelligence });
      qc.invalidateQueries({ queryKey: queryKeys.results });
      qc.invalidateQueries({ queryKey: queryKeys.backtestMatrix });
      qc.invalidateQueries({ queryKey: queryKeys.backtestActive });
      qc.invalidateQueries({ queryKey: queryKeys.reports });
      qc.invalidateQueries({ queryKey: queryKeys.live });
      qc.invalidateQueries({ queryKey: queryKeys.settings });
    },
  });
}

export function useRunWalkforward() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (opts?: import("./api").BacktestOptions) => api.walkforward(opts ?? {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.live });
      qc.invalidateQueries({ queryKey: queryKeys.intelligence });
      qc.invalidateQueries({ queryKey: queryKeys.validation });
    },
  });
}

export function useValidation() {
  return useQuery({
    queryKey: queryKeys.validation,
    queryFn: api.validation,
    enabled: isBrowser,
    staleTime: 45_000,
    refetchInterval: 90_000,
    retry: 1,
    placeholderData: (prev) => prev,
  });
}

export function useRisk() {
  return useQuery({
    queryKey: queryKeys.risk,
    queryFn: api.risk,
    enabled: isBrowser,
    staleTime: 25_000,
    retry: 1,
    placeholderData: (prev) => prev,
  });
}

export function useQuantumStatus() {
  return useQuery({
    queryKey: queryKeys.quantum,
    queryFn: api.quantumStatus,
    enabled: isBrowser,
    staleTime: 15_000,
    refetchInterval: 30_000,
    retry: 1,
  });
}

export function usePlatformStatus() {
  return useQuery({
    queryKey: queryKeys.platform,
    queryFn: api.platformStatus,
    enabled: isBrowser,
    staleTime: 15_000,
    refetchInterval: 30_000,
    retry: 1,
  });
}

export function useUpdateRisk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.updateRisk,
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.risk }),
  });
}

export function useResults(selection?: { strategy: string; timeframe: string; base_asset?: import("./api").OperatedBase } | null) {
  return useQuery({
    queryKey: [...queryKeys.results, selection?.strategy, selection?.timeframe, selection?.base_asset ?? "BTC"],
    queryFn: () =>
      api.results({
        strategy: selection!.strategy,
        timeframe: selection!.timeframe,
        base_asset: selection!.base_asset ?? "BTC",
      }),
    enabled: isBrowser && !!selection,
    staleTime: 0,
  });
}

export function useBacktestActiveJob(enabled = true) {
  return useQuery({
    queryKey: queryKeys.backtestActive,
    queryFn: () => api.backtestAllActive(),
    enabled: isBrowser && enabled,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.active && data.status === "running" ? 2000 : false;
    },
    staleTime: 0,
  });
}

export function useBacktestMatrix() {
  return useQuery({
    queryKey: queryKeys.backtestMatrix,
    queryFn: async (): Promise<BacktestMatrixResponse> => {
      const resetActive = isReportsResetActive();
      try {
        const fresh = normalizeMatrixResponse(await api.backtestMatrix());
        if (fresh.items.length === 0) {
          clearCachedMatrix();
          if (resetActive) clearReportsResetFlag();
          return emptyMatrix(fresh.quote);
        }
        clearReportsResetFlag();
        if (isMatrixHealthy(fresh)) {
          saveCachedMatrix(fresh);
        }
        return fresh;
      } catch (err) {
        const cached = loadCachedMatrix();
        if (cached?.items?.length) return cached;
        if (resetActive) {
          clearCachedMatrix();
          return emptyMatrix();
        }
        throw err;
      }
    },
    enabled: isBrowser,
    initialData: () => loadCachedMatrix() ?? undefined,
    staleTime: 120_000,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    retry: 1,
  });
}

export function useReports() {
  return useQuery({ queryKey: queryKeys.reports, queryFn: api.reports });
}

export function useSettings() {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: api.settings,
    enabled: isBrowser,
    staleTime: 60_000,
    retry: 1,
    placeholderData: (prev) => prev,
  });
}

export function useUpdateOperational() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.updateOperational,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.settings });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard });
      qc.invalidateQueries({ queryKey: queryKeys.live });
    },
  });
}

export function useUpdateOperationalSlots() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.updateOperationalSlots,
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.settings, data);
      qc.invalidateQueries({ queryKey: queryKeys.settings });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard });
      qc.invalidateQueries({ queryKey: queryKeys.live });
      qc.invalidateQueries({ queryKey: queryKeys.intelligence });
    },
  });
}

export function useUpdateKillSwitch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.updateKillSwitch,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.settings });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useUpdateNotifications() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.updateNotifications,
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.settings }),
  });
}

export function useTestTelegram() {
  return useMutation({ mutationFn: api.testTelegram });
}

export function useSystemReset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.resetSystem,
    onSuccess: (res, variables) => {
      if (variables.reports) {
        markReportsReset();
        clearCachedMatrix();
        void qc.cancelQueries({ queryKey: queryKeys.backtestMatrix });
        qc.setQueryData(queryKeys.backtestMatrix, emptyMatrix());
        qc.removeQueries({ queryKey: queryKeys.results });
      }
      qc.invalidateQueries({ queryKey: queryKeys.strategies });
      qc.invalidateQueries({ queryKey: queryKeys.reports });
      if (!variables.reports) {
        qc.invalidateQueries({ queryKey: queryKeys.backtestMatrix });
      }
      qc.invalidateQueries({ queryKey: queryKeys.dashboard });
      qc.invalidateQueries({ queryKey: queryKeys.intelligence });
      qc.invalidateQueries({ queryKey: queryKeys.intelligenceAnalysis });
      qc.invalidateQueries({ queryKey: queryKeys.journal });
      qc.invalidateQueries({ queryKey: queryKeys.validation });
      qc.invalidateQueries({ queryKey: queryKeys.risk });
      qc.invalidateQueries({ queryKey: queryKeys.quantum });
      qc.invalidateQueries({ queryKey: queryKeys.portfolio });
      qc.invalidateQueries({ queryKey: queryKeys.platform });
      return res;
    },
  });
}

export function useAckRiskLock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.ackRiskLock,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.dashboard });
      qc.invalidateQueries({ queryKey: queryKeys.platform });
    },
  });
}
