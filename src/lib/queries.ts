import { useEffect, useState } from "react";
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
  markReportsReset,
  saveCachedMatrix,
} from "./backtest-matrix-store";

/** TanStack Start faz SSR — queries de API só no browser (proxy /atlas-api). */
export const isBrowser = typeof window !== "undefined";

export const queryKeys = {
  dashboard: ["dashboard"] as const,
  markets: ["markets"] as const,
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
    staleTime: 30_000,
    retry: 1,
  });
}

export function useDashboard() {
  return useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: api.dashboard,
    enabled: isBrowser,
    staleTime: 30_000,
    retry: 1,
    refetchInterval: 60_000,
  });
}

export function useMarkets() {
  return useQuery({
    queryKey: queryKeys.markets,
    queryFn: api.markets,
    enabled: isBrowser,
    refetchInterval: 30_000,
    staleTime: 15_000,
    retry: 1,
  });
}

export function usePositions() {
  return useQuery({
    queryKey: queryKeys.positions,
    queryFn: api.positions,
    enabled: isBrowser,
    refetchInterval: 10_000,
    retry: 1,
  });
}

export function useStrategies() {
  return useQuery({ queryKey: queryKeys.strategies, queryFn: api.strategies, enabled: isBrowser, retry: 1 });
}

export function useJournal() {
  return useQuery({ queryKey: queryKeys.journal, queryFn: api.journal, enabled: isBrowser, retry: 1 });
}

export function useIntelligence() {
  return useQuery({
    queryKey: queryKeys.intelligence,
    queryFn: api.intelligence,
    enabled: isBrowser,
    staleTime: 60_000,
    retry: 1,
  });
}

export function useIntelligenceAnalysis(strategy?: string) {
  return useQuery({
    queryKey: [...queryKeys.intelligenceAnalysis, strategy ?? "default"],
    queryFn: () => api.intelligenceAnalysis(strategy),
    enabled: isBrowser,
    staleTime: 60_000,
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
  return useQuery({ queryKey: queryKeys.live, queryFn: api.live, refetchInterval: 10_000 });
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
  return useMutation({
    mutationFn: () => api.backtestAll("USDT", onProgress),
    onSuccess: (data) => {
      const matrix = batchToMatrix(data);
      saveCachedMatrix(matrix);
      qc.setQueryData(queryKeys.backtestMatrix, matrix);
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
  return useQuery({ queryKey: queryKeys.validation, queryFn: api.validation, refetchInterval: 20_000 });
}

export function useRisk() {
  return useQuery({ queryKey: queryKeys.risk, queryFn: api.risk });
}

export function useUpdateRisk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.updateRisk,
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.risk }),
  });
}

export function useResults(selection?: { strategy: string; timeframe: string } | null) {
  return useQuery({
    queryKey: [...queryKeys.results, selection?.strategy, selection?.timeframe],
    queryFn: () => api.results({ strategy: selection!.strategy, timeframe: selection!.timeframe }),
    enabled: isBrowser && !!selection,
    staleTime: 0,
  });
}

export function useBacktestMatrix() {
  return useQuery({
    queryKey: queryKeys.backtestMatrix,
    queryFn: async (): Promise<BacktestMatrixResponse> => {
      const resetActive = isReportsResetActive();
      try {
        const fresh = await api.backtestMatrix();
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
        if (resetActive) {
          clearCachedMatrix();
          return emptyMatrix();
        }
        throw err;
      }
    },
    enabled: isBrowser,
    staleTime: 30_000,
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
    staleTime: 15_000,
    retry: 1,
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
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.settings });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard });
      qc.invalidateQueries({ queryKey: queryKeys.live });
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
