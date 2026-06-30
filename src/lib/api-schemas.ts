import { z } from "zod";

const nullableNumber = z.number().nullable().optional();
const nullableString = z.string().nullable().optional();

export const apiExternalErrorSchema = z
  .object({
    kind: z.string().optional(),
    message: z.string().optional(),
    retryable: z.boolean().optional(),
    status_code: z.number().optional(),
  })
  .passthrough();

export const cacheStatusSchema = z
  .object({
    stale: z.boolean().catch(false).default(false),
    ttl_seconds: nullableNumber,
    age_seconds: nullableNumber,
    last_success_at: nullableString,
    error: z.union([apiExternalErrorSchema, z.string()]).nullable().optional(),
  })
  .passthrough();

export const marketTickerSchema = z
  .object({
    symbol: z.string().catch(""),
    price: z.number().catch(0),
    change_pct: z.number().catch(0),
    volume_24h: z.number().catch(0),
    sparkline: z.array(z.number()).catch([]).default([]),
  })
  .passthrough();

export const marketsResponseSchema = z
  .object({
    items: z.array(marketTickerSchema).catch([]).default([]),
    cache: cacheStatusSchema.optional(),
  })
  .passthrough();

export const marketChartBarSchema = z
  .object({
    t: z.number().catch(0),
    o: z.number().nullable().catch(null),
    h: z.number().nullable().catch(null),
    l: z.number().nullable().catch(null),
    c: z.number().nullable().catch(null),
    ema20: nullableNumber,
    ema200: nullableNumber,
    bb_upper: nullableNumber,
    bb_mid: nullableNumber,
    bb_lower: nullableNumber,
    supertrend: nullableNumber,
  })
  .passthrough();

export const marketChartResponseSchema = z
  .object({
    symbol: z.string().catch(""),
    base: z.string().catch(""),
    timeframe: z.string().catch(""),
    bars: z.array(marketChartBarSchema).catch([]).default([]),
    indicators: z.array(z.string()).optional(),
    updated_at: z.string().optional(),
    stale: z.boolean().catch(false).default(false),
    last_success_at: nullableString,
    ttl_seconds: nullableNumber,
    error: z.union([apiExternalErrorSchema, z.string()]).nullable().optional(),
  })
  .passthrough();

export const botInstanceSchema = z
  .object({
    key: z.string().catch(""),
    strategy: z.string().catch(""),
    strategy_label: z.string().catch(""),
    timeframe: z.string().catch(""),
    symbol: z.string().catch(""),
    ticks: z.number().catch(0),
    last_tick_at: z.string().nullable().catch(null),
    last_error: z.string().nullable().catch(null),
    in_position: z.boolean().catch(false),
    poll_seconds: z.number().catch(0),
    alive: z.boolean().catch(false),
  })
  .passthrough();

export const botStatusSchema = z
  .object({
    running: z.boolean().catch(false),
    mode: z.enum(["paper", "live"]).catch("paper"),
    started_at: z.string().nullable().catch(null),
    strategy: z.string().catch(""),
    performance_30d_pct: z.number().catch(0),
    days_running: z.number().optional(),
    ticks: z.number().optional(),
    last_tick_at: nullableString,
    last_error: nullableString,
    in_position: z.boolean().optional(),
    engine_alive: z.boolean().optional(),
    instance_count: z.number().optional(),
    instances: z.array(botInstanceSchema).catch([]).optional(),
  })
  .passthrough();

export const riskSettingsSchema = z
  .object({
    risk_per_trade_pct: z.number().catch(0),
    max_risk_per_asset_pct: z.number().catch(0).optional(),
    max_risk_per_strategy_pct: z.number().catch(0).optional(),
    max_total_risk_pct: z.number().catch(0).optional(),
    max_exposure_pct: z.number().catch(0).optional(),
    max_exposure_per_asset_pct: z.number().catch(0).optional(),
    max_exposure_per_strategy_pct: z.number().catch(0).optional(),
    max_exposure_per_direction_pct: z.number().catch(0).optional(),
    max_exposure_per_timeframe_pct: z.number().catch(0).optional(),
    target_volatility_pct: z.number().catch(0).optional(),
    atr_risk_multiplier: z.number().catch(0).optional(),
    fractional_kelly: z.number().catch(0).optional(),
    correlation_risk_scale: z.number().catch(0).optional(),
    daily_stop_pct: z.number().catch(0),
    daily_target_pct: z.number().catch(0),
    max_ops_per_day: z.number().catch(0),
    pause_after_losses: z.number().catch(0),
    cooldown_minutes: z.number().catch(0),
    consecutive_losses: z.number().catch(0),
    trades_today: z.number().catch(0),
    daily_pnl: z.number().catch(0),
  })
  .passthrough();

export const riskResponseSchema = z
  .object({
    settings: riskSettingsSchema,
    balance: z.number().catch(0),
    summary: z
      .object({
        max_exposure: z.number().catch(0),
        max_daily_loss: z.number().catch(0),
        daily_target: z.number().catch(0),
        current_exposure: z.number().catch(0).optional(),
        current_exposure_pct: z.number().catch(0).optional(),
        max_total_risk: z.number().catch(0).optional(),
      })
      .passthrough(),
    protections: z.array(z.string()).catch([]).default([]),
    alert: z.string().nullable().catch(null),
  })
  .passthrough();

const platformIssueBlockSchema = z
  .object({
    issues: z.array(z.string()).catch([]).optional(),
  })
  .passthrough();

export const platformStatusSchema = z
  .object({
    system_health: z.number().catch(0),
    strategy_health: z.number().catch(0),
    engine_health: z.number().catch(0),
    data_health: z.number().catch(0),
    alignment_score: z.number().catch(0),
    alignment_breakdown: z.record(z.string(), z.number()).catch({}).default({}),
    regime: z.string().optional(),
    regime_label: z.string().optional(),
    runtime: z
      .object({
        state: z.string().catch("unknown"),
        state_history: z
          .array(
            z
              .object({
                state: z.string().catch("unknown"),
                reason: z.string().catch(""),
                ts: z.string().catch(""),
              })
              .passthrough(),
          )
          .catch([])
          .default([]),
        bot_running: z.boolean().catch(false),
        bot_mode: z.string().catch("paper"),
        risk_locked: z.boolean().catch(false),
      })
      .passthrough(),
    recovery: platformIssueBlockSchema,
    data_quality: platformIssueBlockSchema,
    engine: z.object({}).passthrough().catch({}),
    alerts: z
      .object({
        total: z.number().catch(0),
        groups: z
          .object({
            info: z
              .array(
                z.object({ message: z.string().catch(""), ts: z.string().catch("") }).passthrough(),
              )
              .catch([])
              .default([]),
            warning: z
              .array(
                z.object({ message: z.string().catch(""), ts: z.string().catch("") }).passthrough(),
              )
              .catch([])
              .default([]),
            critical: z
              .array(
                z.object({ message: z.string().catch(""), ts: z.string().catch("") }).passthrough(),
              )
              .catch([])
              .default([]),
          })
          .catch({ info: [], warning: [], critical: [] }),
        recent: z
          .array(
            z.object({ message: z.string().catch(""), ts: z.string().catch("") }).passthrough(),
          )
          .catch([])
          .default([]),
      })
      .passthrough(),
    updated_at: z.string().optional(),
  })
  .passthrough();

export const healthResponseSchema = z
  .object({
    status: z.string().catch("unknown"),
    version: z.string().catch(""),
    bot_running: z.boolean().catch(false),
    bot_mode: z.string().optional(),
    bot_instances: z.number().optional(),
    kill_switch: z.boolean().optional(),
    binance_demo_configured: z.boolean().optional(),
    binance_demo_connected: z.boolean().optional(),
    active_strategy: z.string().optional(),
    active_timeframe: z.string().optional(),
  })
  .passthrough();
