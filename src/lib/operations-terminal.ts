import type {
  BotInstance,
  BotStatus,
  DashboardStats,
  JournalEntry,
  OperationsFeedItem,
  OperationsFeedResponse,
  PlatformStatus,
  Position,
  QuantumStatus,
  RiskResponse,
} from "./api";
import { tvInterval as tvIntervalFromChart } from "./tradingview-chart";

export type StrategyVisualId = "pullback" | "breakout" | "supertrend";
export type HealthTone = "healthy" | "attention" | "degraded";
export type CardTone = "success" | "warning" | "danger";

export type FilterChip = { label: string; ok: boolean };

export type TfRow = { tf: string; ok: boolean | null; label: string };
export type SetupStep = { label: string; ok: boolean | null };

export type StrategyRuntimeView = {
  key: string;
  title: string;
  subtitle: string;
  visual: StrategyVisualId;
  status: "operando" | "monitorando" | "pausado";
  alignmentScore: number;
  healthScore: number;
  healthTone: HealthTone;
  healthLabel: string;
  statusEmoji: string;
  cardTone: CardTone;
  confidence: number;
  regime: string;
  signal: "compra" | "venda" | "aguardando";
  lastAnalysis: string | null;
  nextCandleSec: number | null;
  filters: FilterChip[];
  timeframes: TfRow[];
  setupProgress: number;
  setupSteps: SetupStep[];
  decision: string;
  sparkline: number[];
  lastReason: string | null;
  inPosition: boolean;
};

export type DecisionMotive = { text: string; ok: boolean };

export type DecisionView = {
  regime: string;
  alignmentScore: number;
  entryProbability: number;
  action: string;
  strategyLabel?: string;
  motives: DecisionMotive[];
  timeframes: TfRow[];
  summary: string;
};

export type TimelineEventView = {
  id: string;
  ts: string | null;
  timeLabel: string;
  title: string;
  subtitle?: string;
  detail?: string[];
  tag: string;
  tone: "success" | "danger" | "warning" | "info" | "neutral";
  icon: "signal" | "entry" | "exit" | "error" | "sync" | "hold" | "blocked";
  symbol?: string;
  strategyLabel?: string;
  score?: number;
  decision?: string;
  timeframes?: TfRow[];
  entryProbability?: number;
};

export type HeaderMetrics = {
  capital: number;
  positions: number;
  exposurePct: number;
  latencyMs: number | null;
  uptime: string;
  nextTickSec: number | null;
};

const STRATEGY_VISUAL: Record<string, StrategyVisualId> = {
  pullback_ema20_v1: "pullback",
  breakout_high20_v1: "breakout",
  supertrend_mm200_v1: "supertrend",
};

const MODULE_KEYS: Record<string, string> = {
  pullback_ema20_v1: "pullback_ema20",
  breakout_high20_v1: "breakout_high20",
  supertrend_mm200_v1: "supertrend_mm200",
};

const DEFAULT_CARD_BASE: Omit<
  StrategyRuntimeView,
  "key" | "lastAnalysis" | "nextCandleSec" | "sparkline" | "alignmentScore" | "healthScore" | "healthTone" | "healthLabel" | "statusEmoji" | "cardTone" | "confidence" | "timeframes" | "setupProgress" | "setupSteps" | "regime"
> = {
  title: "",
  subtitle: "BTC/USDT",
  visual: "pullback",
  status: "monitorando",
  signal: "aguardando",
  filters: [],
  decision: "Aguardando oportunidade",
  lastReason: null,
  inPosition: false,
};

const DEFAULT_CARDS_META: { title: string; visual: StrategyVisualId }[] = [
  { title: "Pullback EMA20", visual: "pullback" },
  { title: "Breakout High20", visual: "breakout" },
  { title: "Supertrend + EMA200", visual: "supertrend" },
];

export function fmtTime(ts: string | null | undefined): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return ts.slice(11, 19);
  }
}

export function fmtCountdown(totalSec: number | null | undefined): string {
  if (totalSec == null || totalSec < 0) return "—";
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function fmtUptime(startedAt: string | null | undefined, now = Date.now()): string {
  if (!startedAt) return "—";
  const ms = now - new Date(startedAt).getTime();
  if (ms < 0 || Number.isNaN(ms)) return "—";
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return "<1m";
}

/** Cronômetro HH:MM:SS (ou Nd HH:MM:SS) — atualizar a cada 1s no client. */
export function fmtUptimeClock(startedAt: string | null | undefined, now = Date.now()): string {
  if (!startedAt) return "00:00:00";
  const ms = now - new Date(startedAt).getTime();
  if (ms < 0 || Number.isNaN(ms)) return "00:00:00";

  const totalSec = Math.floor(ms / 1000);
  const d = Math.floor(totalSec / 86_400);
  const h = Math.floor((totalSec % 86_400) / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  const clock = `${pad(h)}:${pad(m)}:${pad(s)}`;
  return d > 0 ? `${d}d ${clock}` : clock;
}

export function tvInterval(timeframe: string): string {
  return tvIntervalFromChart(timeframe);
}

export function healthToneFromScore(score: number): HealthTone {
  if (score >= 85) return "healthy";
  if (score >= 60) return "attention";
  return "degraded";
}

export function healthLabelFromTone(tone: HealthTone): string {
  if (tone === "healthy") return "Saudável";
  if (tone === "attention") return "Atenção";
  return "Degradado";
}

export function statusEmojiFromHealth(score: number): string {
  if (score >= 85) return "🟢";
  if (score >= 60) return "🟡";
  return "🔴";
}

export function cardToneFromHealth(score: number): CardTone {
  if (score >= 85) return "success";
  if (score >= 60) return "warning";
  return "danger";
}

export function inferRegime(
  reason: string | null | undefined,
  quantum?: QuantumStatus,
  platform?: PlatformStatus,
): string {
  const label = quantum?.regime_label ?? platform?.regime_label;
  if (label) return label;
  const r = (reason ?? "").toLowerCase();
  if (r.includes("below ema200") || r.includes("no uptrend")) return "Bear Trend";
  if (r.includes("range")) return "Range";
  if (r.includes("adx too low")) return "Weak Bull";
  if (r.includes("supertrend not bullish")) return "Weak Bull";
  if (r.includes("pullback") || r.includes("bounce")) return "Bull Trend";
  return "Monitorando";
}

export function parseHoldFilters(reason: string | null | undefined): FilterChip[] {
  const r = (reason ?? "").toLowerCase();
  const chips: FilterChip[] = [];

  if (r.includes("ema200") || r.includes("uptrend") || r.includes("below ema")) {
    chips.push({ label: "EMA200", ok: !r.includes("below") && !r.includes("no uptrend") });
  }
  if (r.includes("ema20") || r.includes("pullback")) {
    chips.push({ label: "EMA20", ok: !r.includes("no pullback") && !r.includes("no bullish bounce") });
  }
  if (r.includes("volume")) {
    chips.push({ label: "Volume", ok: !r.includes("low volume") && !r.includes("volume too") });
  }
  if (r.includes("adx")) {
    chips.push({ label: "ADX", ok: !r.includes("adx too low") });
  }
  if (r.includes("supertrend")) {
    chips.push({ label: "Supertrend", ok: !r.includes("not bullish") && !r.includes("flipped bearish") });
  }
  if (r.includes("breakout") || r.includes("high_20")) {
    chips.push({ label: "Breakout", ok: !r.includes("no breakout") });
  }
  if (r.includes("not ready") || r.includes("warming")) {
    chips.push({ label: "Indicadores", ok: false });
  }

  if (chips.length === 0 && r) {
    chips.push({ label: "Condições", ok: false });
  }
  return chips;
}

function signalLabel(raw: string | null | undefined): StrategyRuntimeView["signal"] {
  const s = (raw ?? "hold").toLowerCase();
  if (s.includes("enter") || s === "buy") return "compra";
  if (s.includes("exit") || s === "sell") return "venda";
  return "aguardando";
}

function estimateAlignment(base: number, signal: string | null | undefined, reason: string | null | undefined): number {
  let score = base || 50;
  const s = (signal ?? "hold").toLowerCase();
  const r = (reason ?? "").toLowerCase();
  if (s.includes("enter")) return Math.min(100, score + 12);
  if (r.includes("not ready") || r.includes("warming")) return Math.min(score, 28);
  if (r.includes("below ema200") || r.includes("no uptrend")) return Math.min(score, 43);
  if (r.includes("adx too low")) return Math.min(score, 52);
  if (r.includes("no pullback") || r.includes("no breakout")) return Math.min(score, 58);
  if (s === "hold" && !r) return score;
  return Math.max(20, Math.min(88, score - 5));
}

export function buildTimeframeRows(
  reason: string | null | undefined,
  signal: string | null | undefined,
  visual: StrategyVisualId,
): TfRow[] {
  const r = (reason ?? "").toLowerCase();
  const s = (signal ?? "hold").toLowerCase();
  const enterReady = s.includes("enter");

  const d1Ok = !r.includes("below ema200") && !r.includes("no uptrend");
  const d1Label = d1Ok ? (visual === "supertrend" ? "Bull" : "Alta") : "Abaixo EMA200";

  const h4Ok = d1Ok && !r.includes("adx too low") && !r.includes("supertrend not bullish");
  let h4Label = "Neutro";
  if (h4Ok) h4Label = visual === "breakout" ? "Breakout zone" : "Confirmado";
  else if (r.includes("adx too low")) h4Label = "Tendência fraca";

  const h1Ok =
    enterReady ||
    (!r.includes("no pullback") &&
      !r.includes("no breakout") &&
      !r.includes("no bullish bounce") &&
      !r.includes("not ready") &&
      !r.includes("warming"));
  const h1Label = enterReady ? "Gatilho" : h1Ok ? "Pronto" : "Sem entrada";

  return [
    { tf: "1D", ok: d1Ok, label: d1Label },
    { tf: "4H", ok: h4Ok, label: h4Label },
    { tf: "1H", ok: h1Ok, label: h1Label },
  ];
}

export function buildSetupSteps(timeframes: TfRow[], filters: FilterChip[]): SetupStep[] {
  const steps: SetupStep[] = [
    { label: "1D Trend", ok: timeframes[0]?.ok ?? null },
    { label: "4H Confirm", ok: timeframes[1]?.ok ?? null },
    { label: "1H Trigger", ok: timeframes[2]?.ok ?? null },
  ];
  for (const f of filters) {
    if (["Volume", "ADX", "Supertrend", "Breakout", "EMA20"].includes(f.label)) {
      steps.push({ label: f.label, ok: f.ok });
    }
  }
  return steps;
}

export function computeSetupProgress(steps: SetupStep[]): number {
  const valid = steps.filter((s) => s.ok != null);
  if (!valid.length) return 0;
  const ok = valid.filter((s) => s.ok).length;
  return Math.round((ok / valid.length) * 100);
}

function strategyHealthScore(
  inst: BotInstance,
  alignment: number,
  filters: FilterChip[],
  setupProgress: number,
  quantum?: QuantumStatus,
): number {
  if (inst.last_error) return 22;
  if (inst.in_position) return Math.max(85, Math.min(97, alignment + 18));

  const modKey = MODULE_KEYS[inst.strategy] ?? inst.strategy.replace("_v1", "");
  const modHealth =
    quantum?.module_health?.[modKey] ?? quantum?.module_backtest_stats?.[modKey]?.health_score;

  const passCount = filters.filter((f) => f.ok).length;
  const filterScore = filters.length ? (passCount / filters.length) * 100 : 55;
  const runtimeScore = inst.alive ? 82 : inst.last_tick_at ? 48 : 35;

  let score: number;
  if (modHealth != null) {
    score = modHealth * 0.45 + setupProgress * 0.25 + runtimeScore * 0.2 + filterScore * 0.1;
  } else {
    score = setupProgress * 0.35 + runtimeScore * 0.35 + Math.max(alignment, 35) * 0.3;
  }

  if (inst.ticks > 20 && !inst.last_error) score += 4;
  return Math.round(Math.max(15, Math.min(100, score)));
}

export function entryProbability(
  alignment: number,
  setupProgress: number,
  signal: string | null | undefined,
  inPosition: boolean,
): number {
  const s = (signal ?? "hold").toLowerCase();
  if (inPosition) return Math.min(97, alignment + 8);
  if (s.includes("enter")) return Math.min(97, Math.max(alignment, 72) + 10);
  return Math.round(Math.max(8, Math.min(88, alignment * 0.38 + setupProgress * 0.52)));
}

function matchTickForInstance(instance: BotInstance, items: OperationsFeedItem[]): OperationsFeedItem | undefined {
  if (!instance.last_tick_at) return undefined;
  const target = new Date(instance.last_tick_at).getTime();
  let best: OperationsFeedItem | undefined;
  let bestDelta = Infinity;
  for (const item of items) {
    if (item.event !== "tick" || !item.ts) continue;
    const delta = Math.abs(new Date(item.ts).getTime() - target);
    if (delta < bestDelta && delta < 15_000) {
      bestDelta = delta;
      best = item;
    }
  }
  return best;
}

function matchCardForTick(tick: OperationsFeedItem, cards: StrategyRuntimeView[]): StrategyRuntimeView | undefined {
  if (!tick.ts) return undefined;
  const target = new Date(tick.ts).getTime();
  return cards.find((c) => {
    if (!c.lastAnalysis) return false;
    return Math.abs(new Date(c.lastAnalysis).getTime() - target) < 15_000;
  });
}

function instanceStatus(instance: BotInstance): StrategyRuntimeView["status"] {
  if (instance.last_error) return "pausado";
  if (instance.in_position) return "operando";
  return "monitorando";
}

function nextCandleSec(instance: BotInstance): number | null {
  if (!instance.last_tick_at) return instance.poll_seconds ?? null;
  const elapsed = (Date.now() - new Date(instance.last_tick_at).getTime()) / 1000;
  const poll = instance.poll_seconds ?? 60;
  return Math.max(0, Math.round(poll - elapsed));
}

export function buildOpsStats(
  feed: OperationsFeedResponse,
  quantum?: QuantumStatus,
  platform?: PlatformStatus,
  risk?: RiskResponse,
): DashboardStats {
  const balance = risk?.balance ?? feed.items.find((i) => i.equity)?.equity ?? 5000;
  return {
    balance: Number(balance),
    balance_delta_pct: 0,
    pnl: risk?.settings.daily_pnl ?? 0,
    pnl_delta_pct: 0,
    active_strategy: feed.bot.instances?.[0]?.strategy_label ?? feed.bot.strategy,
    win_rate_pct: 0,
    profit_factor: 0,
    trades_today: risk?.settings.trades_today ?? 0,
    atlas_score: 0,
    bot_running: feed.bot.running,
    bot_mode: feed.mode,
    kill_switch: false,
    balance_source: feed.mode === "live" ? "binance_live" : "binance_demo",
    account_label: feed.mode === "live" ? "Binance Live" : "Binance Demo",
    alignment_score: quantum?.alignment_score ?? platform?.alignment_score ?? 0,
    health_score: quantum?.health_score ?? platform?.system_health ?? 0,
    bot_phase: quantum?.bot_phase ?? (feed.bot.running ? "demo" : "parado"),
    open_positions: feed.bot.instances?.filter((i) => i.in_position).length ?? 0,
  };
}

export function buildHeaderMetrics(
  stats: DashboardStats,
  bot: BotStatus,
  positions: Position[],
  capital: number,
  nextTickSec: number | null,
  latencyMs: number | null,
): HeaderMetrics {
  const notional = positions.reduce((sum, p) => sum + Math.abs(p.entry * (p.side === "short" ? -1 : 1)), 0);
  const exposurePct = capital > 0 ? Math.min(100, (notional / capital) * 100) : 0;
  return {
    capital,
    positions: positions.length || stats.open_positions,
    exposurePct: Math.round(exposurePct * 10) / 10,
    latencyMs,
    uptime: fmtUptime(bot.started_at),
    nextTickSec,
  };
}

export function buildStrategyCards(
  instances: BotInstance[] | undefined,
  feedItems: OperationsFeedItem[],
  stats: DashboardStats,
  quantum: QuantumStatus | undefined,
  platform: PlatformStatus | undefined,
  sparkline: number[],
): StrategyRuntimeView[] {
  const baseScore = stats.alignment_score || platform?.alignment_score || quantum?.alignment_score || 50;
  const regimeBase = inferRegime(quantum?.last_reason ?? null, quantum, platform);

  if (!instances?.length) {
    return DEFAULT_CARDS_META.map((meta, i) => {
      const healthScore = Math.max(45, baseScore - i * 5);
      const tone = healthToneFromScore(healthScore);
      const tfs = buildTimeframeRows(null, "hold", meta.visual);
      const steps = buildSetupSteps(tfs, []);
      const setupProgress = computeSetupProgress(steps);
      return {
        ...DEFAULT_CARD_BASE,
        key: `default-${i}`,
        title: meta.title,
        visual: meta.visual,
        alignmentScore: baseScore,
        healthScore,
        healthTone: tone,
        healthLabel: healthLabelFromTone(tone),
        statusEmoji: statusEmojiFromHealth(healthScore),
        cardTone: cardToneFromHealth(healthScore),
        confidence: entryProbability(baseScore, setupProgress, "hold", false),
        regime: regimeBase,
        timeframes: tfs,
        setupProgress,
        setupSteps: steps,
        lastAnalysis: null,
        nextCandleSec: null,
        sparkline: sparkline.slice(-24),
      };
    });
  }

  return instances.slice(0, 3).map((inst) => {
    const tick = matchTickForInstance(inst, feedItems);
    const reason = tick?.reason ?? quantum?.last_reason ?? null;
    const signalRaw = tick?.signal ?? quantum?.last_signal ?? "hold";
    const visual = STRATEGY_VISUAL[inst.strategy] ?? "pullback";
    const filters = parseHoldFilters(reason);
    const regime = inferRegime(reason, quantum, platform);
    const alignmentScore = estimateAlignment(baseScore, signalRaw, reason);
    const timeframes = buildTimeframeRows(reason, signalRaw, visual);
    const setupSteps = buildSetupSteps(timeframes, filters);
    const setupProgress = computeSetupProgress(setupSteps);
    const healthScore = strategyHealthScore(inst, alignmentScore, filters, setupProgress, quantum);
    const healthTone = healthToneFromScore(healthScore);
    const confidence = entryProbability(alignmentScore, setupProgress, signalRaw, inst.in_position);

    let decision = "Aguardando oportunidade";
    if (inst.last_error) decision = `Pausado · ${inst.last_error}`;
    else if (inst.in_position) decision = "Operação em andamento";
    else if (signalRaw?.toLowerCase().includes("enter")) decision = "Entrada executada";
    else if (filters.length) {
      const blockers = filters.filter((f) => !f.ok).map((f) => f.label.toLowerCase());
      if (blockers.length) decision = `HOLD · ${blockers.join(", ")}`;
    }

    return {
      key: inst.key,
      title: inst.strategy_label,
      subtitle: `${inst.symbol} · ${inst.timeframe.toUpperCase()}`,
      visual,
      status: instanceStatus(inst),
      alignmentScore,
      healthScore,
      healthTone,
      healthLabel: healthLabelFromTone(healthTone),
      statusEmoji: statusEmojiFromHealth(healthScore),
      cardTone: cardToneFromHealth(healthScore),
      confidence,
      regime,
      signal: signalLabel(signalRaw),
      lastAnalysis: inst.last_tick_at,
      nextCandleSec: nextCandleSec(inst),
      filters,
      timeframes,
      setupProgress,
      setupSteps,
      decision,
      sparkline: sparkline.slice(-24),
      lastReason: reason,
      inPosition: inst.in_position,
    };
  });
}

export function buildDecisionView(
  cards: StrategyRuntimeView[],
  stats: DashboardStats,
  quantum?: QuantumStatus,
  platform?: PlatformStatus,
): DecisionView {
  const primary =
    cards.find((c) => c.status === "operando") ??
    cards.reduce<StrategyRuntimeView | undefined>((best, c) => {
      if (!best) return c;
      return c.alignmentScore < best.alignmentScore ? c : best;
    }, undefined) ??
    cards[0];

  if (!primary) {
    const alignment = stats.alignment_score || 50;
    return {
      regime: inferRegime(null, quantum, platform),
      alignmentScore: alignment,
      entryProbability: entryProbability(alignment, 0, "hold", false),
      action: "Aguardando oportunidade",
      motives: [],
      timeframes: [],
      summary: "Runtime aguardando instâncias ativas.",
    };
  }

  const motives: DecisionMotive[] = [];
  for (const tf of primary.timeframes) {
    motives.push({
      text:
        tf.tf === "1D" && !tf.ok
          ? "Preço abaixo EMA200"
          : tf.tf === "4H" && !tf.ok
            ? "Sem confirmação 4H"
            : tf.tf === "1H" && !tf.ok
              ? "Pullback / gatilho não formado"
              : `${tf.tf} ${tf.label}`,
      ok: !!tf.ok,
    });
  }
  for (const f of primary.filters.slice(0, 4)) {
    motives.push({
      text: f.ok ? `${f.label} adequado` : `${f.label} bloqueando`,
      ok: f.ok,
    });
  }

  const summary =
    primary.status === "operando"
      ? `${primary.title} em operação. Health ${primary.healthScore}/100 — gestão ativa.`
      : primary.confidence >= 70
        ? `Setup ${primary.setupProgress}% formado em ${primary.subtitle}. Próximo de entrada.`
        : `Sistema monitorando ${primary.subtitle}. Health ${primary.healthScore}/100 — alignment ${primary.alignmentScore}/100.`;

  return {
    regime: primary.regime,
    alignmentScore: primary.alignmentScore,
    entryProbability: primary.confidence,
    action: primary.decision,
    strategyLabel: primary.title,
    motives: motives.slice(0, 8),
    timeframes: primary.timeframes,
    summary,
  };
}

function timelineTone(event: string, action?: string | null): TimelineEventView["tone"] {
  if (event === "error") return "danger";
  if (event === "entry" || action === "entry") return "success";
  if (event === "exit" || action === "exit") return "danger";
  if (action === "blocked") return "warning";
  return "neutral";
}

function timelineIcon(event: string, action?: string | null): TimelineEventView["icon"] {
  if (event === "error") return "error";
  if (event === "entry" || action === "entry") return "entry";
  if (event === "exit" || action === "exit") return "exit";
  if (event === "reconcile") return "sync";
  if (action === "blocked") return "blocked";
  if (event === "tick") return "hold";
  return "signal";
}

function tfLine(tf: TfRow): string {
  return `${tf.tf} ${tf.ok ? "✅" : "❌"} ${tf.label}`;
}

function enrichTickTitle(
  item: OperationsFeedItem,
  card?: StrategyRuntimeView,
  symbol?: string,
): Pick<
  TimelineEventView,
  "title" | "subtitle" | "detail" | "symbol" | "strategyLabel" | "score" | "decision" | "timeframes" | "entryProbability"
> {
  const reason = item.reason ?? "";
  const signal = (item.signal ?? "hold").toLowerCase();
  const tfs = card?.timeframes ?? buildTimeframeRows(reason, signal, "pullback");
  const score = card?.alignmentScore ?? estimateAlignment(50, signal, reason);
  const prob = card?.confidence ?? entryProbability(score, computeSetupProgress(buildSetupSteps(tfs, parseHoldFilters(reason))), signal, false);
  const stratLabel = card?.title ?? item.message?.split("·")[0]?.trim();
  const sym = symbol ?? "BTCUSDT";

  if (item.action === "entry") {
    return {
      title: "Entrada executada",
      subtitle: stratLabel,
      symbol: sym,
      strategyLabel: stratLabel,
      score,
      entryProbability: prob,
      decision: "ENTER",
      timeframes: tfs,
      detail: [sym, stratLabel ?? "", ...tfs.map(tfLine), `Score: ${Math.round(score)}/100`, "Entrada executada"],
    };
  }
  if (item.action === "exit") {
    return {
      title: "Posição encerrada",
      subtitle: reason || item.message,
      symbol: sym,
      strategyLabel: stratLabel,
      score,
      decision: "EXIT",
      timeframes: tfs,
      detail: [sym, reason || item.message, `Score: ${Math.round(score)}/100`].filter(Boolean),
    };
  }
  if (item.action === "blocked") {
    const filters = parseHoldFilters(reason);
    return {
      title: "Entrada bloqueada",
      subtitle: reason,
      symbol: sym,
      strategyLabel: stratLabel,
      score,
      entryProbability: prob,
      decision: "BLOCKED",
      timeframes: tfs,
      detail: [sym, ...tfs.map(tfLine), ...filters.map((f) => `${f.ok ? "✅" : "❌"} ${f.label}`), `Score: ${Math.round(score)}/100`],
    };
  }
  if (item.status === "warming_up") {
    return { title: "Aquecendo indicadores", subtitle: item.message, symbol: sym, score, decision: "WARMUP" };
  }
  if (signal.includes("enter")) {
    return {
      title: "Sinal de compra detectado",
      subtitle: stratLabel,
      symbol: sym,
      strategyLabel: stratLabel,
      score,
      entryProbability: prob,
      decision: "SIGNAL",
      timeframes: tfs,
      detail: [sym, stratLabel ?? "", ...tfs.map(tfLine), `Score: ${Math.round(score)}/100`],
    };
  }

  return {
    title: "Monitorando mercado",
    subtitle: stratLabel ?? inferRegime(reason),
    symbol: sym,
    strategyLabel: stratLabel,
    score,
    entryProbability: prob,
    decision: "HOLD",
    timeframes: tfs,
    detail: [
      sym,
      stratLabel ?? "",
      ...tfs.map(tfLine),
      `Score: ${Math.round(score)}/100`,
      "Decisão: HOLD",
      reason ? reason.slice(0, 120) : inferRegime(reason),
    ].filter(Boolean),
  };
}

export function buildTimelineEvents(
  items: OperationsFeedItem[],
  journal: JournalEntry[],
  cards: StrategyRuntimeView[] = [],
  symbol = "BTCUSDT",
): TimelineEventView[] {
  const fromFeed: TimelineEventView[] = items
    .filter((item) => item.event !== "runner_start")
    .slice(0, 40)
    .map((item, i) => {
      const card = matchCardForTick(item, cards);
      const enriched = enrichTickTitle(item, card, symbol.replace("/", ""));
      return {
        id: `${item.ts}-${item.event}-${i}`,
        ts: item.ts,
        timeLabel: fmtTime(item.ts),
        title: enriched.title,
        subtitle: enriched.subtitle ?? item.message,
        detail: enriched.detail,
        tag: item.event.toUpperCase(),
        tone: timelineTone(item.event, item.action),
        icon: timelineIcon(item.event, item.action),
        symbol: enriched.symbol,
        strategyLabel: enriched.strategyLabel,
        score: enriched.score,
        decision: enriched.decision,
        timeframes: enriched.timeframes,
        entryProbability: enriched.entryProbability,
      };
    });

  const fromJournal: TimelineEventView[] = journal.slice(0, 8).map((j, i) => ({
    id: `j-${j.ts}-${i}`,
    ts: j.ts ?? null,
    timeLabel: fmtTime(j.ts),
    title: j.event === "entry" ? "Entrada registrada" : "Saída registrada",
    subtitle: j.reason ?? undefined,
    detail: [
      symbol.replace("/", ""),
      j.entry_module ? j.entry_module : "",
      j.alignment_score != null ? `Score: ${Math.round(j.alignment_score)}/100` : "",
      j.regime_label ? `Regime: ${j.regime_label}` : "",
    ].filter(Boolean),
    tag: j.event?.toUpperCase() ?? "TRADE",
    tone: j.event === "entry" ? "success" : "info",
    icon: j.event === "entry" ? "entry" : "exit",
    score: j.alignment_score,
    decision: j.event === "entry" ? "ENTER" : "EXIT",
  }));

  return [...fromFeed, ...fromJournal]
    .sort((a, b) => {
      const ta = a.ts ? new Date(a.ts).getTime() : 0;
      const tb = b.ts ? new Date(b.ts).getTime() : 0;
      return tb - ta;
    })
    .slice(0, 30);
}

export function botHeaderLabel(bot: BotStatus | undefined, mode: string): string {
  if (!bot?.running) return "Parado";
  if (bot.last_error) return "Com erro";
  return mode === "live" ? "Operando Live" : "Operando";
}

export function exchangeLabel(stats: DashboardStats, mode: string): string {
  if (mode === "live" || stats.balance_source === "binance_live") return "Binance Live";
  return "Binance Demo";
}

export type TradeOverlay = {
  id: string;
  strategy: string;
  entry: number;
  current: number;
  stop?: number;
  target?: number;
  trailing?: number;
  pnlPct: number;
  score?: number;
  regime?: string;
};

export function buildTradeOverlays(positions: Position[], journal: JournalEntry[]): TradeOverlay[] {
  return positions.map((p, i) => {
    const j = journal.find((e) => e.event === "entry");
    const stop = typeof j?.fill === "object" && j.fill && "stop_price" in j.fill ? Number(j.fill.stop_price) : undefined;
    const target = p.entry > 0 ? p.entry * 1.03 : undefined;
    const trailing = p.current > p.entry ? p.entry + (p.current - p.entry) * 0.5 : undefined;
    return {
      id: `${p.asset}-${i}`,
      strategy: p.strategy,
      entry: p.entry,
      current: p.current,
      stop: stop || p.entry * 0.98,
      target,
      trailing,
      pnlPct: p.pnl_pct,
      score: j?.alignment_score ?? undefined,
      regime: j?.regime_label ?? undefined,
    };
  });
}
