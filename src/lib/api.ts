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
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(
        "Tempo esgotado — confirme que a API Python está ativa (python -m atlas.cli api).",
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

export const api = {
  health: () =>
    request<HealthResponse>("/health"),
  dashboard: () => request<DashboardResponse>("/dashboard"),
  quantumStatus: () => request<QuantumStatus>("/quantum/status"),
  portfolio: () => request<PortfolioResponse>("/portfolio"),
  markets: () => request<{ items: MarketTicker[] }>("/markets"),
  positions: () => request<{ items: Position[] }>("/positions"),
  strategies: () => request<{ items: Strategy[] }>("/strategies"),
  journal: () => request<{ items: JournalEntry[] }>("/journal"),
  intelligence: () => request<IntelligenceResponse>("/intelligence"),
  intelligenceAnalysis: (strategy?: string) =>
    request<IntelligenceAnalysis>(
      strategy ? `/intelligence/analysis?strategy=${encodeURIComponent(strategy)}` : "/intelligence/analysis",
    ),
  botStatus: () => request<BotStatus>("/bot/status"),
  botStart: () => request<BotStatus>("/bot/start", { method: "POST" }),
  botStartLive: () => request<BotStatus>("/bot/start-live", { method: "POST" }),
  botStop: () => request<BotStatus>("/bot/stop", { method: "POST" }),
  live: async (): Promise<LiveResponse> => {
    try {
      return await request<LiveResponse>("/live");
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
  liveGates: () => request<LiveGatesResponse>("/live/gates"),
  operationsFeed: (limit = 100) =>
    request<OperationsFeedResponse>(`/operations/feed?limit=${limit}`),
  backtest: (opts: BacktestOptions = {}) =>
    request<{ metrics: BacktestMetrics; report_path: string; strategy?: string; timeframe?: string }>(
      "/backtest",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy: opts.strategy ?? "mm200_trend_v2",
          timeframe: opts.timeframe ?? "4h",
          quote: opts.quote ?? "USDT",
          config_path: opts.config_path,
        }),
      },
    ),
  walkforward: (opts: BacktestOptions = {}, train_pct = 0.7) =>
    request<{ ok: boolean; report_path: string }>("/research/walkforward", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        strategy: opts.strategy ?? "mm200_trend_v2",
        timeframe: opts.timeframe ?? "4h",
        quote: opts.quote ?? "USDT",
        config_path: opts.config_path,
        train_pct,
      }),
    }),
  backtestAllStatus: (jobId: string) =>
    request<BacktestAllJobResponse>(`/backtest/all/${encodeURIComponent(jobId)}`, {
      timeoutMs: 30_000,
    }),
  backtestMatrix: (quote = "USDT") =>
    request<BacktestMatrixResponse>(`/backtest/matrix?quote=${encodeURIComponent(quote)}`),
  backtestAll: async (
    quote = "USDT",
    onProgress?: (progress: BacktestAllProgress) => void,
  ): Promise<BacktestAllResponse> => {
    const started = await request<BacktestAllJobResponse>("/backtest/all", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timeframes: ["1h", "4h", "1d"], quote }),
      timeoutMs: 60_000,
    });

    if (started.status === "done" && started.total_runs != null) {
      return started as BacktestAllResponse;
    }
    // API antiga (resposta síncrona sem job_id) — compatível até reiniciar o servidor
    if (!started.job_id && started.total_runs != null) {
      return started as BacktestAllResponse;
    }

    const jobId = started.job_id;
    if (!jobId) {
      throw new ApiError("Resposta inválida ao iniciar matriz de backtests.", 500);
    }

    const emit = (job: BacktestAllJobResponse) => {
      onProgress?.({
        completed: job.completed,
        total: job.total,
        current: job.current ?? undefined,
        status: job.status,
      });
    };
    emit(started);

    const deadline = Date.now() + 600_000;
    while (Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      const job = await api.backtestAllStatus(jobId);
      emit(job);
      if (job.status === "done") {
        return job as BacktestAllResponse;
      }
      if (job.status === "error") {
        throw new ApiError(job.error ?? "Matriz de backtests falhou.", 500);
      }
    }
    throw new ApiError(
      "Tempo esgotado aguardando matriz — a API pode estar sobrecarregada ou offline.",
      408,
    );
  },
  validation: () => request<ValidationResponse>("/validation"),
  risk: () => request<RiskResponse>("/risk"),
  updateRisk: (body: Partial<RiskSettings>) =>
    request<RiskResponse>("/risk", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  results: (opts?: { strategy?: string; timeframe?: string }) => {
    if (opts?.strategy && opts?.timeframe) {
      return request<ResultsResponse>(
        `/results/${encodeURIComponent(opts.strategy)}/${encodeURIComponent(opts.timeframe)}`,
      );
    }
    const params = new URLSearchParams();
    if (opts?.strategy) params.set("strategy", opts.strategy);
    if (opts?.timeframe) params.set("timeframe", opts.timeframe);
    const q = params.toString();
    return request<ResultsResponse>(`/results${q ? `?${q}` : ""}`);
  },
  reports: () => request<ReportsResponse>("/reports"),
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
  updateKillSwitch: (active: boolean) =>
    request<SettingsResponse>("/settings/kill-switch", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active }),
    }),
  updateNotifications: (body: Partial<Record<string, boolean>>) =>
    request<SettingsResponse>("/settings/notifications", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  testTelegram: () => request<{ ok: boolean; configured: boolean }>("/alerts/test", { method: "POST" }),
  resetSystem: (body: SystemResetRequest) =>
    request<SystemResetResponse>("/system/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  platformStatus: () => request<PlatformStatus>("/platform/status"),
  ackRiskLock: () => request<{ ok: boolean }>("/platform/ack-risk", { method: "POST" }),
  runStressTest: () => request<{ ok: boolean; reports: unknown[] }>("/platform/stress-test", { method: "POST" }),
};

export type BacktestOptions = {
  strategy?: string;
  timeframe?: OperationalTimeframe;
  quote?: string;
  config_path?: string;
};

export type BacktestBatchItem = {
  strategy: string;
  strategy_label: string;
  timeframe: string;
  ok: boolean;
  config_path?: string;
  report_path?: string;
  error?: string;
  result?: "lucro" | "prejuizo" | "empate";
  metrics?: BacktestMetrics;
};

export type BacktestAllProgress = {
  completed: number;
  total: number;
  current?: string;
  status: string;
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
  timeframes: string[];
  quote: string;
  best: BacktestBatchItem | null;
  items: BacktestBatchItem[];
  errors: { strategy: string; timeframe: string; error: string }[];
};

export type BacktestMatrixResponse = {
  total: number;
  quote: string;
  best_return: BacktestBatchItem | null;
  best_score: BacktestBatchItem | null;
  items: BacktestBatchItem[];
};

export type OperationalTimeframe = "1h" | "4h" | "1d";

export type OperationalUpdate = {
  strategy: string;
  timeframe: OperationalTimeframe;
  quote?: string;
};

export type PaperSlotConfig = {
  strategy: string;
  timeframe: OperationalTimeframe;
  quote?: string;
  enabled: boolean;
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
  module_status?: Record<string, { active?: boolean; triggered?: boolean; confidence?: number | null; reason?: string }>;
  module_health?: Record<string, number>;
  module_backtest_stats?: Record<string, { trades: number; win_rate_pct: number; profit_factor: number; max_drawdown_pct: number; health_score: number }>;
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
  recovery: Record<string, unknown>;
  data_quality: Record<string, unknown>;
  engine: Record<string, unknown>;
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

export type DashboardResponse = {
  stats: DashboardStats;
  equity_curve: { day: string; equity: number }[];
  drawdown_curve?: { day: string; drawdown_pct: number }[];
  radar_data: { axis: string; v: number }[];
  positions: Position[];
  flow: { label: string; status: string; pct: number; color: string }[];
  quantum?: QuantumStatus;
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
  analysis?: {
    strategy?: string;
    market?: string;
    timeframe?: string;
    level1: Level1Snapshot;
    level2: Level2Snapshot | null;
    level3: Level3Snapshot | null;
  };
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
  win_rate_pct: number;
  trades: number;
  expectancy: number;
  atlas_score: number;
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
  daily_stop_pct: number;
  daily_target_pct: number;
  max_ops_per_day: number;
  pause_after_losses: number;
  cooldown_minutes: number;
  consecutive_losses: number;
  trades_today: number;
  daily_pnl: number;
};

export type RiskResponse = {
  settings: RiskSettings;
  balance: number;
  summary: { max_exposure: number; max_daily_loss: number; daily_target: number };
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
    bot_running: boolean;
    bot_mode: "paper" | "live";
  };
  operational?: {
    strategies: { id: string; name: string }[];
    timeframes: string[];
    quotes: string[];
    max_slots?: number;
    slots?: {
      strategy: string;
      strategy_label: string;
      timeframe: string;
      quote: string;
      enabled: boolean;
      key: string;
    }[];
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
