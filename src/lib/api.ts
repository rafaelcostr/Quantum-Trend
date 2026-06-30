import type { ZodType, ZodTypeDef } from "zod";
import {
  botStatusSchema,
  healthResponseSchema,
  marketChartResponseSchema,
  marketsResponseSchema,
  platformStatusSchema,
  riskResponseSchema,
} from "./api-schemas";

function apiBase(): string {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL.replace(/\/$/, "");
  }
  if (import.meta.env.DEV) {
    // SSR (Node) não passa pelo proxy do Vite
    if (typeof window === "undefined") {
      return "http://127.0.0.1:8000/api";
    }
    // Browser: mesmo origin evita CORS (TanStack captura /api)
    return "/atlas-api";
  }
  return "/api";
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function parseErrorDetail(text: string, status: number): string {
  const trimmed = text.trim();
  if (trimmed.startsWith("<!") || trimmed.includes("<html") || trimmed.includes("dumper-dump")) {
    if (status === 502 || status === 503) {
      return "API Python indisponível — execute python -m atlas.cli api na porta 8000.";
    }
    return "Erro interno no servidor — reinicie npm run dev e a API Python.";
  }
  try {
    const json = JSON.parse(trimmed) as { detail?: string | unknown; message?: string };
    if (typeof json.detail === "string") return json.detail;
    if (Array.isArray(json.detail)) return json.detail.map(String).join("; ");
    if (typeof json.message === "string") return json.message;
  } catch {
    /* plain text */
  }
  return trimmed.length > 280 ? `${trimmed.slice(0, 280)}…` : trimmed || `Erro HTTP ${status}`;
}

async function request<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const timeoutMs = init?.timeoutMs ?? 20_000;
  const { timeoutMs: _, ...fetchInit } = init ?? {};
  let signal = fetchInit.signal;
  let timer: ReturnType<typeof setTimeout> | undefined;

  if (!signal) {
    if (typeof AbortSignal !== "undefined" && "timeout" in AbortSignal) {
      signal = AbortSignal.timeout(timeoutMs);
    } else if (typeof AbortController !== "undefined") {
      const controller = new AbortController();
      timer = setTimeout(() => controller.abort(), timeoutMs);
      signal = controller.signal;
    }
  }

  try {
    const res = await fetch(`${apiBase()}${path}`, {
      headers: { Accept: "application/json", ...(fetchInit.headers ?? {}) },
      ...fetchInit,
      signal,
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => res.statusText);
      throw new ApiError(parseErrorDetail(detail || res.statusText, res.status), res.status);
    }
    const contentType = res.headers.get("content-type") ?? "";
    if (!contentType.includes("application/json")) {
      const body = await res.text().catch(() => "");
      throw new ApiError(parseErrorDetail(body, res.status), res.status);
    }
    return res.json() as Promise<T>;
  } catch (err) {
    const timedOut =
      (err instanceof DOMException && err.name === "AbortError") ||
      (err instanceof Error && /timed out|abort/i.test(err.message));
    if (timedOut) {
      throw new ApiError(
        "Tempo esgotado — a API respondeu devagar (com 3 bots pode levar ~30s). Aguarde ou reinicie a API.",
        408,
      );
    }
    if (err instanceof TypeError) {
      throw new ApiError(
        "Não foi possível contactar a API — execute python -m atlas.cli api na porta 8000.",
        0,
      );
    }
    throw err;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

async function requestSchema<T>(
  path: string,
  schema: ZodType<T, ZodTypeDef, unknown>,
  init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const data = await request<unknown>(path, init);
  const parsed = schema.safeParse(data);
  if (!parsed.success) {
    const first = parsed.error.issues[0];
    throw new ApiError(
      `Resposta inválida da API em ${path}: ${first?.path.join(".") || "payload"} ${first?.message ?? ""}`.trim(),
      502,
    );
  }
  return parsed.data;
}

export const api = {
  health: () => requestSchema<HealthResponse>("/health", healthResponseSchema),
  dashboard: () => request<DashboardResponse>("/dashboard", { timeoutMs: 35_000 }),
  quantumStatus: () => request<QuantumStatus>("/quantum/status", { timeoutMs: 30_000 }),
  portfolio: () => request<PortfolioResponse>("/portfolio", { timeoutMs: 35_000 }),
  markets: () =>
    requestSchema<MarketsResponse>("/markets", marketsResponseSchema, { timeoutMs: 12_000 }),
  marketChart: (base: string, timeframe: string, quote = "USDT") =>
    requestSchema<MarketChartResponse>(
      `/markets/chart?base=${encodeURIComponent(base)}&quote=${encodeURIComponent(quote)}&timeframe=${encodeURIComponent(timeframe)}`,
      marketChartResponseSchema,
      { timeoutMs: 25_000 },
    ),
  backtestChart: (strategy: string, timeframe: string, baseAsset: string = "BTC", quote = "USDT") =>
    request<BacktestChartResponse>(
      `/backtests/chart?strategy=${encodeURIComponent(strategy)}&timeframe=${encodeURIComponent(timeframe)}&base_asset=${encodeURIComponent(baseAsset)}&quote=${encodeURIComponent(quote)}`,
      { timeoutMs: 60_000 },
    ),
  positions: () => request<{ items: Position[] }>("/positions", { timeoutMs: 45_000 }),
  strategies: () => request<{ items: Strategy[] }>("/strategies"),
  journal: () => request<{ items: JournalEntry[] }>("/journal", { timeoutMs: 15_000 }),
  intelligence: () => request<IntelligenceResponse>("/intelligence", { timeoutMs: 15_000 }),
  intelligenceAnalysis: (strategy?: string) =>
    request<IntelligenceAnalysis | null>(
      strategy
        ? `/intelligence/analysis?strategy=${encodeURIComponent(strategy)}`
        : "/intelligence/analysis",
      { timeoutMs: 60_000 },
    ),
  botStatus: () => requestSchema<BotStatus>("/bot/status", botStatusSchema),
  botStart: () => request<BotStatus>("/bot/start", { method: "POST", timeoutMs: 120_000 }),
  botStartLive: (confirmText = "") =>
    request<BotStatus>("/bot/start-live", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm_text: confirmText }),
      timeoutMs: 120_000,
    }),
  botStop: () => request<BotStatus>("/bot/stop", { method: "POST" }),
  live: async (): Promise<LiveResponse> => {
    try {
      return await request<LiveResponse>("/live", { timeoutMs: 90_000 });
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        throw new ApiError(
          "Endpoint /api/live não encontrado — a API Python precisa ser reiniciada após a atualização (python -m atlas.cli api).",
          404,
        );
      }
      throw e;
    }
  },
  liveGates: () => request<LiveGatesResponse>("/live/gates", { timeoutMs: 60_000 }),
  operationsFeed: (limit = 100) =>
    request<OperationsFeedResponse>(`/operations/feed?limit=${limit}`, { timeoutMs: 45_000 }),
  backtest: (opts: BacktestOptions = {}) =>
    request<{
      metrics: BacktestMetrics;
      report_path: string;
      strategy?: string;
      timeframe?: string;
    }>("/backtest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        strategy: opts.strategy ?? "mm200_trend_v2",
        timeframe: opts.timeframe ?? "4h",
        quote: opts.quote ?? "USDT",
        base_asset: opts.base_asset ?? "BTC",
        config_path: opts.config_path,
      }),
    }),
  walkforward: (opts: BacktestOptions = {}, train_pct = 0.7) =>
    request<WalkforwardResponse>("/research/walkforward", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        strategy: opts.strategy ?? "mm200_trend_v2",
        timeframe: opts.timeframe ?? "4h",
        quote: opts.quote ?? "USDT",
        base_asset: opts.base_asset ?? "BTC",
        config_path: opts.config_path,
        train_pct,
      }),
    }),
  backtestAllStatus: (jobId: string) =>
    request<BacktestAllJobResponse>(`/backtest/all/${encodeURIComponent(jobId)}`, {
      timeoutMs: 45_000,
    }),
  backtestAllActive: () =>
    request<BacktestAllJobResponse & { active?: boolean }>("/backtest/all/active", {
      timeoutMs: 15_000,
    }),
  backtestMatrix: (quote = "USDT") =>
    request<BacktestMatrixResponse>(`/backtest/matrix?quote=${encodeURIComponent(quote)}`),
  backtestAll: async (
    quote = "USDT",
    baseAsset: OperatedBase = "BTC",
    onProgress?: (progress: BacktestAllProgress) => void,
  ): Promise<BacktestAllResponse> => {
    const emit = (job: BacktestAllJobResponse) => {
      onProgress?.({
        completed: job.completed,
        total: job.total,
        current: job.current ?? undefined,
        status: job.status,
        base_asset: job.base_asset,
        quote: job.quote,
        asset_label: job.asset_label,
      });
    };

    const pollUntilDone = async (jobId: string): Promise<BacktestAllResponse> => {
      const deadline = Date.now() + 7_200_000; // 2 h — 45 backtests podem levar bastante tempo
      let idlePolls = 0;
      while (Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, idlePolls > 0 ? 2500 : 800));
        let job: BacktestAllJobResponse;
        try {
          job = await api.backtestAllStatus(jobId);
        } catch (err) {
          if (err instanceof ApiError && err.status === 404) {
            throw new ApiError(
              "Job de backtest perdido — reinicie a API Python (python -m atlas.cli api) e rode a matriz novamente.",
              404,
            );
          }
          throw err;
        }
        emit(job);
        if (job.status === "done") {
          const okCount = job.items?.filter((i) => i.ok).length ?? job.completed ?? 0;
          if (okCount === 0 && (job.failed ?? 0) > 0) {
            const sample = job.errors?.[0]?.error ?? "Verifique logs da API.";
            throw new ApiError(`Matriz concluída sem sucessos. ${sample}`, 500);
          }
          return job as BacktestAllResponse;
        }
        if (job.status === "error") {
          throw new ApiError(job.error ?? "Matriz de backtests falhou.", 500);
        }
        idlePolls += 1;
      }
      throw new ApiError(
        "Tempo esgotado (2h) aguardando matriz — deixe a API rodando ou teste menos estratégias.",
        408,
      );
    };

    let started: BacktestAllJobResponse;
    try {
      started = await request<BacktestAllJobResponse>("/backtest/all", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ timeframes: ["1h", "4h", "1d"], quote, base_asset: baseAsset }),
        timeoutMs: 120_000,
      });
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError("Falha ao iniciar matriz de backtests.", 500);
    }

    if (started.status === "done" && started.total_runs != null) {
      return started as BacktestAllResponse;
    }
    if (!started.job_id && started.total_runs != null) {
      return started as BacktestAllResponse;
    }

    const jobId = started.job_id;
    if (!jobId) {
      throw new ApiError(
        "API desatualizada ou offline — reinicie com python -m atlas.cli api e tente novamente.",
        500,
      );
    }

    emit(started);
    return pollUntilDone(jobId);
  },
  validation: () => request<ValidationResponse>("/validation"),
  risk: () => requestSchema<RiskResponse>("/risk", riskResponseSchema, { timeoutMs: 20_000 }),
  updateRisk: (body: Partial<RiskSettings>) =>
    request<RiskResponse>("/risk", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  results: (opts?: { strategy?: string; timeframe?: string; base_asset?: OperatedBase }) => {
    const base = opts?.base_asset ?? "BTC";
    if (opts?.strategy && opts?.timeframe) {
      return request<ResultsResponse>(
        `/results/${encodeURIComponent(opts.strategy)}/${encodeURIComponent(opts.timeframe)}?base_asset=${base}`,
      );
    }
    const params = new URLSearchParams();
    if (opts?.strategy) params.set("strategy", opts.strategy);
    if (opts?.timeframe) params.set("timeframe", opts.timeframe);
    params.set("base_asset", base);
    const q = params.toString();
    return request<ResultsResponse>(`/results${q ? `?${q}` : ""}`);
  },
  reports: () => request<ReportsResponse>("/reports"),
  quantLabExperiments: () =>
    request<QuantLabExperimentsResponse>("/quant-lab/experiments", { timeoutMs: 25_000 }),
  updateQuantLabAnnotation: (experimentId: string, body: QuantLabAnnotationUpdate) =>
    request<{ ok: boolean; annotation: QuantLabAnnotation }>(
      `/quant-lab/experiments/${encodeURIComponent(experimentId)}/annotation`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        timeoutMs: 15_000,
      },
    ),
  compareQuantLabExperiments: (experimentIds: string[]) =>
    request<QuantLabComparison>("/quant-lab/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ experiment_ids: experimentIds }),
      timeoutMs: 25_000,
    }),
  quantLabReplay: (experimentId: string) =>
    request<QuantLabReplay>(`/quant-lab/replay/${encodeURIComponent(experimentId)}`, {
      timeoutMs: 25_000,
    }),
  quantLabStrategies: () =>
    request<QuantLabStrategyLibrary>("/quant-lab/strategies", { timeoutMs: 25_000 }),
  updateQuantLabStrategyStatus: (strategyId: string, body: QuantLabStrategyStatusUpdate) =>
    request<{ ok: boolean; strategy: QuantLabStrategyStatusUpdate & { id: string } }>(
      `/quant-lab/strategies/${encodeURIComponent(strategyId)}/status`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        timeoutMs: 15_000,
      },
    ),
  settings: () => request<SettingsResponse>("/settings"),
  updateOperational: (body: OperationalUpdate) =>
    request<SettingsResponse>("/settings/operational", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  updateOperationalSlots: (slots: PaperSlotConfig[]) =>
    request<SettingsResponse>("/settings/operational/slots", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slots }),
    }),
  updateKillSwitch: (
    active: boolean,
    opts?: { scope?: "global" | "asset" | "strategy"; key?: string; reason?: string },
  ) =>
    request<SettingsResponse>("/settings/kill-switch", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active, ...(opts ?? {}) }),
    }),
  updateNotifications: (body: Partial<Record<string, boolean>>) =>
    request<SettingsResponse>("/settings/notifications", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  testTelegram: () =>
    request<{ ok: boolean; configured: boolean }>("/alerts/test", { method: "POST" }),
  resetSystem: (body: SystemResetRequest) =>
    request<SystemResetResponse>("/system/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  platformStatus: () =>
    requestSchema<PlatformStatus>("/platform/status", platformStatusSchema, { timeoutMs: 60_000 }),
  monitoringHealth: () => request<MonitoringHealth>("/monitoring/health", { timeoutMs: 20_000 }),
  monitoringIncidents: (status?: string) =>
    request<MonitoringHealth["incidents"] | { status: string; total: number; items: Incident[] }>(
      status
        ? `/monitoring/incidents?status=${encodeURIComponent(status)}`
        : "/monitoring/incidents",
      { timeoutMs: 15_000 },
    ),
  resolveIncident: (incidentId: string) =>
    request<{ ok: boolean; incident: Incident }>(
      `/monitoring/incidents/${encodeURIComponent(incidentId)}/resolve`,
      { method: "POST", timeoutMs: 15_000 },
    ),
  ackRiskLock: () => request<{ ok: boolean }>("/platform/ack-risk", { method: "POST" }),
  runStressTest: () =>
    request<{ ok: boolean; reports: unknown[] }>("/platform/stress-test", { method: "POST" }),
};

export type OperatedBase = "BTC" | "ETH";
export type MarketType = "bull" | "bear" | "range";

export type ApiExternalError = {
  kind?: string;
  message?: string;
  retryable?: boolean;
  status_code?: number;
  [key: string]: unknown;
};

export type CacheStatus = {
  stale: boolean;
  ttl_seconds?: number | null;
  age_seconds?: number | null;
  last_success_at?: string | null;
  error?: ApiExternalError | string | null;
  [key: string]: unknown;
};

export type BacktestOptions = {
  strategy?: string;
  timeframe?: OperationalTimeframe;
  quote?: string;
  base_asset?: OperatedBase;
  config_path?: string;
};

export type BacktestBatchItem = {
  strategy: string;
  strategy_label: string;
  timeframe: string;
  market_type?: "bull" | "bear" | "range";
  base_asset?: OperatedBase;
  ok: boolean;
  config_path?: string;
  report_path?: string;
  error?: string;
  result?: "lucro" | "prejuizo" | "empate";
  metrics?: BacktestMetrics;
  period_start?: string | null;
  period_end?: string | null;
  period_days?: number | null;
};

export type BacktestRankings = {
  by_return?: BacktestBatchItem[];
  by_drawdown?: BacktestBatchItem[];
  by_sharpe?: BacktestBatchItem[];
  by_stability?: BacktestBatchItem[];
  by_risk_adjusted_return?: BacktestBatchItem[];
};

export type BacktestMatrixGroup = {
  market_type: "bull" | "bear" | "range";
  label: string;
  total: number;
  best_return?: BacktestBatchItem | null;
  items: BacktestBatchItem[];
};

export type BacktestAllProgress = {
  completed: number;
  total: number;
  current?: string;
  status: string;
  base_asset?: OperatedBase;
  quote?: string;
  asset_label?: string;
};

export type BacktestAllJobResponse = BacktestAllProgress & {
  job_id: string;
  started_at?: number;
  finished_at?: number | null;
  error?: string;
} & Partial<BacktestAllResponse>;

export type BacktestAllResponse = {
  total_runs: number;
  completed: number;
  failed: number;
  strategy_count?: number;
  timeframes: string[];
  quote: string;
  base_asset?: OperatedBase;
  best: BacktestBatchItem | null;
  items: BacktestBatchItem[];
  groups?: BacktestMatrixGroup[];
  rankings?: BacktestRankings;
  errors: { strategy: string; timeframe: string; error: string }[];
};

export type BacktestMatrixResponse = {
  total: number;
  quote: string;
  best_return: BacktestBatchItem | null;
  best_score: BacktestBatchItem | null;
  items: BacktestBatchItem[];
  groups?: BacktestMatrixGroup[];
  rankings?: BacktestRankings;
  by_asset?: Partial<Record<OperatedBase, Omit<BacktestMatrixResponse, "by_asset">>>;
};

export type QuantLabTag = "promissor" | "rejeitado" | "overfit" | "bom em alta" | "bom em lateral";
export type QuantLabStrategyStatus = "active" | "archived" | "experimental";

export type QuantLabAnnotation = {
  tags?: QuantLabTag[];
  note?: string;
  updated_at?: string | null;
};

export type QuantLabAnnotationUpdate = {
  tags?: QuantLabTag[];
  note?: string;
};

export type QuantLabExperiment = {
  id: string;
  strategy: string;
  strategy_label: string;
  strategy_version: string;
  parameters: Record<string, unknown>;
  timeframe: string;
  asset: string;
  quote: string;
  market: string;
  period_start: string | null;
  period_end: string | null;
  period_days: number | null;
  code_version: string;
  tested_at: string;
  report_path: string;
  metrics: Partial<BacktestMetrics>;
  tags: QuantLabTag[];
  note: string;
  updated_at?: string | null;
};

export type QuantLabExperimentsResponse = {
  items: QuantLabExperiment[];
  total: number;
  allowed_tags: QuantLabTag[];
};

export type QuantLabCurvePoint = {
  index?: number;
  timestamp: string;
  equity?: number;
  drawdown_pct?: number;
};

export type QuantLabComparison = {
  experiments: QuantLabExperiment[];
  equity_curves: { id: string; label: string; points: QuantLabCurvePoint[] }[];
  drawdown_curves: { id: string; points: QuantLabCurvePoint[] }[];
  metrics: ({ id: string } & Partial<BacktestMetrics>)[];
  ranking: ({ id: string } & Partial<BacktestMetrics>)[];
  best_id: string | null;
};

export type QuantLabReplayEvent = {
  index: number;
  timestamp: string;
  equity: number;
  signal: "entry" | "exit" | "hold" | string;
  reason: string;
  entry_count: number;
  exit_count: number;
  indicators: Record<string, unknown>;
};

export type QuantLabReplay = {
  experiment: QuantLabExperiment;
  events: QuantLabReplayEvent[];
  total_events: number;
  total_trades: number;
};

export type QuantLabStrategyLibraryItem = {
  id: string;
  label: string;
  status: QuantLabStrategyStatus;
  market_type: MarketType;
  versions: string[];
  experiment_count: number;
  last_tested_at: string | null;
  note: string;
};

export type QuantLabStrategyLibrary = {
  items: QuantLabStrategyLibraryItem[];
  statuses: QuantLabStrategyStatus[];
};

export type QuantLabStrategyStatusUpdate = {
  status: QuantLabStrategyStatus;
  note?: string;
};

export type OperationalTimeframe = "1h" | "4h" | "1d";

export type OperationalUpdate = {
  strategy: string;
  timeframe: OperationalTimeframe;
  quote?: string;
  base_asset?: OperatedBase;
};

export type PaperSlotConfig = {
  strategy: string;
  strategy_label?: string;
  timeframe: OperationalTimeframe;
  quote?: string;
  base?: OperatedBase;
  symbol?: string;
  enabled: boolean;
  key?: string;
};

export type BotInstance = {
  key: string;
  strategy: string;
  strategy_label: string;
  timeframe: string;
  symbol: string;
  ticks: number;
  last_tick_at: string | null;
  last_error: string | null;
  in_position: boolean;
  poll_seconds: number;
  alive: boolean;
};

export type HealthResponse = {
  status: string;
  version: string;
  bot_running: boolean;
  bot_mode?: string;
  bot_instances?: number;
  kill_switch?: boolean;
  binance_demo_configured?: boolean;
  binance_demo_connected?: boolean;
  active_strategy?: string;
  active_timeframe?: string;
};

export type Position = {
  asset: string;
  side: string;
  entry: number;
  current: number;
  pnl: number;
  pnl_pct: number;
  strategy: string;
  color: string;
};

export type Strategy = {
  id: string;
  name: string;
  winrate: number;
  pf: number;
  dd: number;
  status: string;
  market_type?: MarketType;
  strategy_category?: MarketType;
  trades?: number;
  strategy_type?: string;
};

export type PlatformEngineStatus = {
  binance_latency_ms?: number | null;
  broker_status?: string | null;
  recovery_status?: string | null;
  [key: string]: unknown;
};

export type PlatformRecoveryStatus = {
  ok?: boolean;
  position_source?: string | null;
  reconciled_at?: string | null;
  issues?: string[];
  [key: string]: unknown;
};

export type PlatformDataQualityStatus = {
  score?: number | null;
  candle_count?: number | null;
  last_candle_ts?: string | null;
  issues?: string[];
  [key: string]: unknown;
};

export type JournalEntry = {
  date?: string;
  asset?: string;
  entry?: number;
  exit?: number;
  pnl?: number;
  strategy?: string;
  ts?: string;
  event?: string;
  symbol?: string;
  reason?: string;
  alignment_score?: number;
  regime_label?: string;
  entry_module?: string;
  indicators?: Record<string, unknown>;
  candle?: Record<string, number | string>;
  fill?: Record<string, unknown>;
};

export type MarketTicker = {
  symbol: string;
  price: number;
  change_pct: number;
  volume_24h: number;
  sparkline: number[];
};

export type MarketsResponse = {
  items: MarketTicker[];
  cache?: CacheStatus;
};

export type MarketChartBar = {
  t: number;
  o: number | null;
  h: number | null;
  l: number | null;
  c: number | null;
  ema20?: number | null;
  ema200?: number | null;
  bb_upper?: number | null;
  bb_mid?: number | null;
  bb_lower?: number | null;
  supertrend?: number | null;
};

export type MarketChartResponse = {
  symbol: string;
  base: string;
  timeframe: string;
  bars: MarketChartBar[];
  indicators?: string[];
  updated_at?: string;
  stale?: boolean;
  last_success_at?: string | null;
  ttl_seconds?: number | null;
  error?: ApiExternalError | string | null;
};

export type BacktestChartBar = {
  t: number;
  o: number;
  h: number;
  l: number;
  c: number;
};

export type BacktestChartMarker = {
  t: number;
  kind: "entry" | "exit";
  side: "long" | "short";
  win: boolean;
  pnl: number;
  pnl_pct: number;
  price?: number | null;
  label?: string;
  trade_index?: number;
};

export type BacktestChartResponse = {
  symbol: string;
  strategy: string;
  strategy_label: string;
  timeframe: string;
  base: string;
  period_start?: string | null;
  period_end?: string | null;
  bar_count?: number;
  bars: BacktestChartBar[];
  markers: BacktestChartMarker[];
  summary?: {
    trades: number;
    wins: number;
    losses: number;
    win_rate_pct: number;
    total_return_pct?: number | null;
    profit_factor?: number | null;
    max_drawdown_pct?: number | null;
    atlas_score?: number | null;
  };
  updated_at?: string;
  error?: string;
};

export type DashboardStats = {
  balance: number;
  balance_delta_pct: number;
  pnl: number;
  pnl_delta_pct: number;
  active_strategy: string;
  win_rate_pct: number;
  profit_factor: number;
  trades_today: number;
  atlas_score: number;
  bot_running: boolean;
  bot_mode: "paper" | "live";
  kill_switch: boolean;
  balance_source: "binance_demo" | "binance_live" | "api_error" | "unavailable" | "unknown";
  account_label: string;
  alignment_score: number;
  health_score: number;
  bot_phase: string;
  open_positions: number;
};

export type QuantumStatus = {
  strategy: string;
  bot_phase: string;
  alignment_score: number;
  alignment_breakdown: Record<string, number>;
  alignment_history: { ts: string; score: number }[];
  health_score: number;
  health_history: { ts: string; score: number }[];
  regime?: string;
  regime_label?: string;
  last_signal?: string;
  last_reason?: string;
  entry_module?: string;
  entry_confidence?: number;
  entry_result?: string;
  module_status?: Record<
    string,
    { active?: boolean; triggered?: boolean; confidence?: number | null; reason?: string }
  >;
  module_health?: Record<string, number>;
  module_backtest_stats?: Record<
    string,
    {
      trades: number;
      win_rate_pct: number;
      profit_factor: number;
      max_drawdown_pct: number;
      health_score: number;
    }
  >;
  rejected_modules?: { module: string; confidence: number; reason: string; detail?: string }[];
  updated_at?: string;
};

export type PortfolioResponse = {
  portfolio: {
    total_capital: number;
    available_capital: number;
    allocated_capital: number;
    current_exposure_pct: number;
    max_exposure_pct: number;
    daily_pnl: number;
    weekly_pnl: number;
    monthly_pnl: number;
    annualized_return_pct: number;
  };
  open_positions: number;
  stats_30d: Record<string, number>;
  monthly_returns: { month: string; return_pct: number }[];
  risk: Record<string, unknown>;
  equity_curve?: { day: string; equity: number }[];
  drawdown_curve?: { day: string; drawdown_pct: number }[];
  drawdown_summary?: { current_pct: number; max_pct: number };
  strategy_performance?: {
    strategy_id: string;
    label: string;
    timeframe: string;
    pnl_pct: number;
    trades: number;
    win_rate_pct: number;
    profit_factor: number;
    source?: string;
  }[];
  allocation?: { label: string; strategy_id: string; pct: number }[];
  open_positions_detail?: {
    asset: string;
    strategy: string;
    entry: number;
    current: number;
    pnl_pct: number;
    pnl: number;
    side: string;
  }[];
  portfolio_stats?: {
    win_rate_pct: number;
    profit_factor: number;
    total_return_pct: number;
    sharpe_ratio: number;
    max_drawdown_pct: number;
    total_trades: number;
  };
  monthly_heatmap?: { month: string; return_pct: number; tone: "good" | "bad" | "neutral" }[];
  health?: {
    score: number;
    state: string;
    tone: "success" | "warning" | "danger";
    components: Record<string, number>;
  };
  advanced_risk?: {
    exposure: {
      total_usdt: number;
      total_pct: number;
      by_asset: Record<string, number>;
      by_direction: Record<string, number>;
      by_timeframe: Record<string, number>;
      by_strategy: Record<string, number>;
      correlated_usdt: number;
      positions: {
        slot?: string;
        asset: string;
        symbol: string;
        strategy: string;
        timeframe: string;
        direction: string;
        notional: number;
      }[];
    };
    risk_allocation: {
      strategy_id: string;
      label: string;
      asset: string;
      timeframe: string;
      risk_budget_usdt: number;
      max_strategy_risk_usdt: number;
      max_asset_risk_usdt: number;
    }[];
    limits: Record<string, number>;
    sizing: {
      volatility_target_pct: number;
      atr_multiplier: number;
      fractional_kelly: number;
      drawdown_scaling: boolean;
      recommended_scale: number;
    };
    alerts: string[];
  };
};

export type PlatformStatus = {
  system_health: number;
  strategy_health: number;
  engine_health: number;
  data_health: number;
  alignment_score: number;
  alignment_breakdown: Record<string, number>;
  regime?: string;
  regime_label?: string;
  runtime: {
    state: string;
    state_history: { state: string; reason: string; ts: string }[];
    bot_running: boolean;
    bot_mode: string;
    last_decision?: { narrative?: string; outcome?: string; ts?: string };
    last_sync?: string;
    next_analysis?: string;
    risk_locked: boolean;
    risk_lock_reason?: string;
  };
  recovery: PlatformRecoveryStatus;
  data_quality: PlatformDataQualityStatus;
  engine: PlatformEngineStatus;
  monitoring?: MonitoringHealth;
  alerts: {
    total: number;
    groups: {
      info: { message: string; ts: string }[];
      warning: { message: string; ts: string }[];
      critical: { message: string; ts: string }[];
    };
    recent: { message: string; ts: string }[];
  };
  score_explanation?: {
    total: number;
    threshold: number;
    components: { key: string; label: string; score: number; max: number }[];
  };
  capital_scaling?: { current_risk_pct?: number; paused?: boolean };
  trend_exhaustion?: { exhausted?: boolean; reason?: string };
  last_decision?: { narrative?: string; outcome?: string };
  decisions?: unknown[];
  stress_reports?: unknown[];
  updated_at?: string;
};

export type Incident = {
  id: string;
  key: string;
  type: string;
  message: string;
  severity: "info" | "warning" | "critical" | string;
  module: string;
  strategy?: string | null;
  status: "open" | "resolved" | string;
  opened_at: string;
  updated_at: string;
  resolved_at?: string | null;
  count?: number;
  metadata?: Record<string, unknown>;
};

export type MonitoringHealth = {
  api: { online: boolean; status: string; checked_at?: string };
  binance: {
    online: boolean;
    status?: string;
    latency_ms?: number | null;
    credentials_configured?: boolean;
  };
  bot: {
    active: boolean;
    mode?: string;
    instance_count?: number;
    instances?: unknown[];
  };
  last_tick_at?: string | null;
  last_order?: Record<string, unknown> | null;
  last_reconciliation_at?: string | null;
  last_error?: string | null;
  recovery?: Record<string, unknown>;
  regime?: {
    stale?: boolean;
    last_candle_ts?: string | null;
    candle_count?: number;
  };
  health: {
    score: number;
    issues: string[];
    last_tick_stale?: boolean;
    last_reconciliation_stale?: boolean;
  };
  incidents: {
    total: number;
    open: number;
    resolved: number;
    channels: Record<string, boolean>;
    items: Incident[];
    open_items: Incident[];
  };
};

export type MarketRegimeSnapshot = {
  available: boolean;
  stale?: boolean;
  last_success_at?: string | null;
  ttl_seconds?: number | null;
  symbol: string;
  timeframe: string;
  market_type: "bull" | "bear" | "range";
  label: string;
  suggestion: string;
  strategies_route: string;
  accent: "success" | "destructive" | "warning";
  reason: string;
  close: number | null;
  ema200: number | null;
  adx: number | null;
  price_vs_ema_pct: number | null;
  candle_at: string | null;
  updated_at: string;
  aligned_with_bot: boolean;
  enabled_slots: number;
  matching_slots: number;
  active_market_types: string[];
  active_market_labels: string[];
  slot_details: {
    strategy: string;
    strategy_label: string;
    timeframe: string;
    market_type: string;
    operates_now: boolean;
  }[];
  warning: string | null;
  error: ApiExternalError | string | null;
  stale_snapshot?: MarketRegimeSnapshot | null;
};

export type DashboardResponse = {
  stats: DashboardStats;
  equity_curve: { day: string; equity: number }[];
  drawdown_curve?: { day: string; drawdown_pct: number }[];
  radar_data: { axis: string; v: number }[];
  positions: Position[];
  flow: { label: string; status: string; pct: number; color: string }[];
  quantum?: QuantumStatus;
  market_regime?: MarketRegimeSnapshot;
  platform?: PlatformStatus;
  account?: {
    equity_usdt: number;
    quote_asset: string;
    quote_total: number;
    quote_free: number;
    base_asset: string;
    base_total: number;
    base_free: number;
  } | null;
  spark_up: number[];
  spark_down: number[];
  spark_mix: number[];
};

export type IntelligenceResponse = {
  strategies_evaluated: number;
  best_strategy: string;
  best_score: number;
  overall_score: number;
  strategies: Strategy[];
  heatmap: { sym: string; score: number }[];
  selection?: IntelligenceSelectionPayload;
};

export type IntelligencePick = {
  strategy: string;
  name: string;
  timeframe: OperationalTimeframe;
  quote?: string;
  base?: OperatedBase;
  enabled: boolean;
  market_type: "bull" | "bear" | "range";
  atlas_score?: number | null;
  pf?: number | null;
  winrate?: number | null;
  dd?: number | null;
  return_pct?: number | null;
  source: "backtest" | "default";
};

export type IntelligenceRankedStrategy = {
  rank: number;
  strategy: string;
  name: string;
  timeframe: OperationalTimeframe;
  market_type: "bull" | "bear" | "range";
  atlas_score?: number | null;
  pf: number;
  winrate: number;
  dd: number;
  return_pct: number;
};

export type IntelligencePack = {
  id: "bull_range" | "bear_range";
  label: string;
  description: string;
  route: string;
  peer_route: string;
  trend_type: "bull" | "bear";
  slots: IntelligencePick[];
  backtest_count: number;
};

export type IntelligenceAssetSelection = {
  base: OperatedBase;
  atlas_score: number;
  total_backtests: number;
  groups: {
    bull: IntelligenceRankedStrategy[];
    bear: IntelligenceRankedStrategy[];
    range: IntelligenceRankedStrategy[];
  };
  packs: {
    bull_range: IntelligencePack;
    bear_range: IntelligencePack;
  };
};

export type IntelligenceSelectionPayload = {
  slots_per_asset: number;
  trend_slots: number;
  range_slots: number;
  assets: IntelligenceAssetSelection[];
};

export type MetricReading = {
  key: string;
  label: string;
  value: number | string | null;
  display: string;
  status: string;
  emoji: string;
  status_text: string;
};

export type EducationalMetric = {
  reading: MetricReading;
  what_is: string;
  why_matters: string;
  how_interpret: string;
  bands_text: string;
};

export type Level1Snapshot = {
  atlas_score: number;
  score_label: string;
  score_emoji: string;
  confidence: string;
  confidence_emoji: string;
  overfitting_risk: string;
  overfitting_emoji: string;
  metrics: MetricReading[];
  strengths: string[];
  weaknesses: string[];
  risks: string[];
  summary: string;
  promotion_backtest_paper: { label: string; ok: boolean; value: string }[];
};

export type Level2Snapshot = {
  metrics: EducationalMetric[];
  diagnosis: string;
  values: Record<string, number | null>;
};

export type Level3Snapshot = {
  metrics: EducationalMetric[];
  diagnosis: string;
  overfitting_risk: string;
  overfitting_emoji: string;
  values: Record<string, number | null>;
  has_walkforward: boolean;
};

export type IntelligenceAnalysis = {
  strategy: string;
  source: string;
  market: string;
  timeframe: string;
  period_start: string | null;
  period_end: string | null;
  level1: Level1Snapshot;
  level2: Level2Snapshot | null;
  level3: Level3Snapshot | null;
  metadata: Record<string, unknown>;
};

export type BotStatus = {
  running: boolean;
  mode: "paper" | "live";
  started_at: string | null;
  strategy: string;
  performance_30d_pct: number;
  days_running?: number;
  ticks?: number;
  last_tick_at?: string | null;
  last_error?: string | null;
  in_position?: boolean;
  engine_alive?: boolean;
  instance_count?: number;
  instances?: BotInstance[];
};

export type LiveGateCheck = { label: string; ok: boolean; value: string };

export type LiveGatesResponse = {
  eligible: boolean;
  checks: LiveGateCheck[];
  checks_passed: number;
  checks_total: number;
  blocking_reasons: string[];
  paper_days: number;
  min_paper_days: number;
  live_symbol: string;
  live_strategy: string;
  requires_opt_in: boolean;
};

export type LiveResponse = {
  gates: LiveGatesResponse;
  bot: BotStatus;
  config: {
    symbol: string;
    timeframe: string;
    strategy: string;
    use_exchange_stop: boolean;
  };
  instances?: BotInstance[];
};

export type OperationsFeedItem = {
  ts: string | null;
  event: string;
  symbol: string | null;
  signal?: string | null;
  reason?: string | null;
  action?: string | null;
  equity?: number | null;
  status?: string | null;
  message: string;
};

export type OperationsFeedResponse = {
  items: OperationsFeedItem[];
  bot: BotStatus;
  mode: "paper" | "live";
  poll_seconds: number | null;
  next_tick_in: number | null;
};

export type BacktestMetrics = {
  total_return_pct: number;
  profit_factor: number;
  max_drawdown_pct: number;
  sharpe: number;
  sortino?: number;
  calmar?: number;
  win_rate_pct: number;
  trades: number;
  expectancy: number;
  payoff_ratio?: number;
  recovery_factor?: number;
  drawdown_duration_bars?: number;
  exposure_time_pct?: number;
  turnover?: number;
  var_95_pct?: number;
  cvar_95_pct?: number;
  stability_score?: number;
  atlas_score: number;
};

export type BacktestResult = {
  metrics: BacktestMetrics;
  report_path: string;
  strategy?: string;
  timeframe?: string;
};

export type PromotionChecklistItem = {
  label: string;
  ok: boolean;
  value: string;
  stage: string;
};

export type WalkforwardResponse = {
  ok: boolean;
  report_path: string;
  robustness?: {
    score?: number;
    approved?: boolean;
    flags?: string[];
    risk_of_ruin_pct?: number;
    monthly_concentration_pct?: number;
    positive_rolling_windows_pct?: number;
    max_validation_drawdown_pct?: number;
  };
  monte_carlo?: {
    simulations?: number;
    risk_of_ruin_pct?: number | null;
    return_p05_pct?: number;
    return_median_pct?: number;
    drawdown_p95_pct?: number;
    worst_sequence_return_pct?: number | null;
    worst_sequence_drawdown_pct?: number;
  };
  holdout?: {
    net_profit_pct?: number;
    profit_factor?: number;
    max_drawdown_pct?: number;
    total_trades?: number;
  } | null;
  rolling_windows?: {
    index: number;
    test_trades: number;
    efficiency?: number | null;
    test?: {
      net_profit_pct?: number;
      profit_factor?: number;
      max_drawdown_pct?: number;
      total_trades?: number;
    };
  }[];
  promotion_checklist?: PromotionChecklistItem[];
};

export type ValidationResponse = {
  score: number;
  criteria_passed: number;
  criteria_total: number;
  criteria: { label: string; ok: boolean; val: string }[];
  stats: {
    pnl: number;
    win_rate: number;
    profit_factor: number;
    drawdown: number;
    trades: number;
    days_running: number;
  };
  bot_running: boolean;
  bot_mode?: "paper" | "live";
  live_gates?: LiveGatesResponse;
  spark_up: number[];
  spark_down: number[];
  spark_mix: number[];
};

export type RiskSettings = {
  risk_per_trade_pct: number;
  max_risk_per_asset_pct?: number;
  max_risk_per_strategy_pct?: number;
  max_total_risk_pct?: number;
  max_exposure_pct?: number;
  max_exposure_per_asset_pct?: number;
  max_exposure_per_strategy_pct?: number;
  max_exposure_per_direction_pct?: number;
  max_exposure_per_timeframe_pct?: number;
  target_volatility_pct?: number;
  atr_risk_multiplier?: number;
  fractional_kelly?: number;
  correlation_risk_scale?: number;
  daily_stop_pct: number;
  daily_target_pct: number;
  max_ops_per_day: number;
  pause_after_losses: number;
  cooldown_minutes: number;
  consecutive_losses: number;
  trades_today: number;
  daily_pnl: number;
};

export type RiskConfig = RiskSettings;

export type RiskResponse = {
  settings: RiskSettings;
  balance: number;
  summary: {
    max_exposure: number;
    max_daily_loss: number;
    daily_target: number;
    current_exposure?: number;
    current_exposure_pct?: number;
    max_total_risk?: number;
  };
  exposure?: NonNullable<PortfolioResponse["advanced_risk"]>["exposure"];
  protections: string[];
  alert: string | null;
};

export type ResultsResponse = {
  title: string;
  strategy: string;
  timeframe: string;
  metrics: BacktestMetrics;
  equity_curve: { day: string; equity: number }[];
  monthly_returns: { m: string; r: number }[];
  distribution: { bucket: string; n: number }[];
  period_start?: string | null;
  period_end?: string | null;
  period_days?: number | null;
  advanced_metrics?: Record<string, number | string | null>;
  costs?: Record<string, number | string | null>;
  period_analysis?: {
    monthly?: { period: string; return_pct: number; start_equity?: number; end_equity?: number }[];
    weekly?: { period: string; return_pct: number; start_equity?: number; end_equity?: number }[];
    yearly?: { period: string; return_pct: number; start_equity?: number; end_equity?: number }[];
    by_asset?: {
      bucket: string;
      trades: number;
      net_pnl: number;
      win_rate_pct: number;
      profit_factor: number;
    }[];
    by_timeframe?: {
      bucket: string;
      trades: number;
      net_pnl: number;
      win_rate_pct: number;
      profit_factor: number;
    }[];
    by_regime?: {
      bucket: string;
      trades: number;
      net_pnl: number;
      win_rate_pct: number;
      profit_factor: number;
    }[];
  };
  overfitting?: {
    stability_score?: number;
    parameter_sensitivity?: string;
    train_test_gap_pct?: number | null;
    flags?: string[];
  };
  spark_up: number[];
  spark_mix: number[];
};

export type ReportsResponse = {
  monthly_returns: { m: string; r: number }[];
  equity_curve: { day: string; equity: number }[];
  summary: string[][];
};

export type SettingsResponse = {
  profile: { name: string; email: string; plan: string };
  exchanges: { name: string; connected: boolean; active: boolean }[];
  notifications: Record<string, boolean>;
  system: {
    strategy: string;
    strategy_id: string;
    symbol: string;
    timeframe: string;
    poll_seconds: number;
    kill_switch: boolean;
    kill_switches?: {
      assets?: Record<string, { active?: boolean; reason?: string; updated_at?: string }>;
      strategies?: Record<string, { active?: boolean; reason?: string; updated_at?: string }>;
    };
    bot_running: boolean;
    bot_mode: "paper" | "live";
  };
  operational?: {
    strategies: Strategy[];
    timeframes: string[];
    quotes: string[];
    bases?: OperatedBase[];
    max_slots?: number;
    max_slots_per_base?: number;
    slots?: PaperSlotConfig[];
    active: {
      strategy: string;
      strategy_label: string;
      timeframe: string;
      symbol: string;
      quote: string;
      poll_seconds: number;
    };
  };
  telegram: { configured: boolean; chat_id_set: boolean };
  alert_channels?: Record<string, boolean>;
};

export type SystemResetRequest = {
  reports?: boolean;
  ohlcv_cache?: boolean;
  paper_demo?: boolean;
};

export type SystemResetResponse = {
  ok: boolean;
  deleted_files: string[];
  cleared_files: string[];
  risk_counters_reset: boolean;
  quantum_state_cleared: boolean;
  deleted_count: number;
  cleared_count: number;
};
