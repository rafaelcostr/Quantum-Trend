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

export type StrategyVisualId = "pullback" | "breakout" | "supertrend";

export type FilterChip = { label: string; ok: boolean };

export type StrategyRuntimeView = {
  key: string;
  title: string;
  subtitle: string;
  visual: StrategyVisualId;
  status: "operando" | "monitorando" | "pausado";
  alignmentScore: number;
  regime: string;
  signal: "compra" | "venda" | "aguardando";
  lastAnalysis: string | null;
  nextCandleSec: number | null;
  filters: FilterChip[];
  decision: string;
  sparkline: number[];
  lastReason: string | null;
  inPosition: boolean;
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
};

const STRATEGY_VISUAL: Record<string, StrategyVisualId> = {
  pullback_ema20_v1: "pullback",
  breakout_high20_v1: "breakout",
  supertrend_mm200_v1: "supertrend",
};

const DEFAULT_CARDS: Omit<StrategyRuntimeView, "key" | "lastAnalysis" | "nextCandleSec" | "sparkline">[] = [
  {
    title: "Pullback EMA20",
    subtitle: "BTC/USDT",
    visual: "pullback",
    status: "monitorando",
    alignmentScore: 0,
    regime: "—",
    signal: "aguardando",
    filters: [],
    decision: "Aguardando oportunidade",
    lastReason: null,
    inPosition: false,
  },
  {
    title: "Breakout High20",
    subtitle: "BTC/USDT",
    visual: "breakout",
    status: "monitorando",
    alignmentScore: 0,
    regime: "—",
    signal: "aguardando",
    filters: [],
    decision: "Aguardando oportunidade",
    lastReason: null,
    inPosition: false,
  },
  {
    title: "Supertrend + EMA200",
    subtitle: "BTC/USDT",
    visual: "supertrend",
    status: "monitorando",
    alignmentScore: 0,
    regime: "—",
    signal: "aguardando",
    filters: [],
    decision: "Aguardando oportunidade",
    lastReason: null,
    inPosition: false,
  },
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

export function tvInterval(timeframe: string): string {
  const tf = timeframe.toLowerCase();
  if (tf === "1d" || tf === "d") return "D";
  if (tf === "4h") return "240";
  if (tf === "1h") return "60";
  if (tf === "15m") return "15";
  return "240";
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

export function buildStrategyCards(
  instances: BotInstance[] | undefined,
  feedItems: OperationsFeedItem[],
  stats: DashboardStats,
  quantum: QuantumStatus | undefined,
  platform: PlatformStatus | undefined,
  sparkline: number[],
): StrategyRuntimeView[] {
  const baseScore = stats.alignment_score || platform?.alignment_score || quantum?.alignment_score || 50;

  if (!instances?.length) {
    return DEFAULT_CARDS.map((c, i) => ({
      ...c,
      key: `default-${i}`,
      alignmentScore: baseScore,
      regime: inferRegime(null, quantum, platform),
      lastAnalysis: null,
      nextCandleSec: null,
      sparkline: sparkline.slice(-24),
    }));
  }

  return instances.slice(0, 3).map((inst) => {
    const tick = matchTickForInstance(inst, feedItems);
    const reason = tick?.reason ?? null;
    const signalRaw = tick?.signal ?? "hold";
    const visual = STRATEGY_VISUAL[inst.strategy] ?? "pullback";
    const filters = parseHoldFilters(reason);
    const regime = inferRegime(reason, quantum, platform);
    const alignmentScore = estimateAlignment(baseScore, signalRaw, reason);

    let decision = "Aguardando oportunidade";
    if (inst.last_error) decision = `Pausado · ${inst.last_error}`;
    else if (inst.in_position) decision = "Operação em andamento";
    else if (signalRaw?.toLowerCase().includes("enter")) decision = "Sinal de compra detectado";
    else if (filters.length) {
      const blockers = filters.filter((f) => !f.ok).map((f) => f.label.toLowerCase());
      if (blockers.length) decision = `Aguardando · ${blockers.join(", ")}`;
    }

    return {
      key: inst.key,
      title: inst.strategy_label,
      subtitle: `${inst.symbol} · ${inst.timeframe.toUpperCase()}`,
      visual,
      status: instanceStatus(inst),
      alignmentScore,
      regime,
      signal: signalLabel(signalRaw),
      lastAnalysis: inst.last_tick_at,
      nextCandleSec: nextCandleSec(inst),
      filters,
      decision,
      sparkline: sparkline.slice(-24),
      lastReason: reason,
      inPosition: inst.in_position,
    };
  });
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

function enrichTickTitle(item: OperationsFeedItem): { title: string; subtitle?: string; detail?: string[] } {
  const reason = item.reason ?? "";
  const signal = (item.signal ?? "hold").toLowerCase();

  if (item.action === "entry") {
    return { title: "Entrada executada", subtitle: reason || item.message };
  }
  if (item.action === "exit") {
    return { title: "Posição encerrada", subtitle: reason || item.message };
  }
  if (item.action === "blocked") {
    return {
      title: "Entrada bloqueada",
      subtitle: reason,
      detail: parseHoldFilters(reason).map((f) => `${f.ok ? "✅" : "❌"} ${f.label}`),
    };
  }
  if (item.status === "warming_up") {
    return { title: "Aquecendo indicadores", subtitle: item.message };
  }
  if (signal.includes("enter")) {
    return { title: "Sinal de compra detectado", subtitle: reason };
  }

  const filters = parseHoldFilters(reason);
  return {
    title: "Monitorando mercado",
    subtitle: inferRegime(reason),
    detail: [
      `Estado: Monitorando`,
      `Regime: ${inferRegime(reason)}`,
      ...filters.map((f) => `${f.ok ? "✅" : "❌"} ${f.label}${f.ok ? "" : reason.includes("below") ? " — abaixo do filtro" : ""}`),
      `Decisão: Aguardando oportunidade`,
    ],
  };
}

export function buildTimelineEvents(items: OperationsFeedItem[], journal: JournalEntry[]): TimelineEventView[] {
  const fromFeed: TimelineEventView[] = items
    .filter((item) => item.event !== "runner_start")
    .slice(0, 40)
    .map((item, i) => {
      const enriched = enrichTickTitle(item);
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
      };
    });

  const fromJournal: TimelineEventView[] = journal.slice(0, 8).map((j, i) => ({
    id: `j-${j.ts}-${i}`,
    ts: j.ts ?? null,
    timeLabel: fmtTime(j.ts),
    title: j.event === "entry" ? "Entrada registrada" : "Saída registrada",
    subtitle: j.reason ?? undefined,
    detail: [
      j.entry_module ? `Módulo: ${j.entry_module}` : "",
      j.alignment_score != null ? `Score: ${Math.round(j.alignment_score)}` : "",
      j.regime_label ? `Regime: ${j.regime_label}` : "",
    ].filter(Boolean),
    tag: j.event?.toUpperCase() ?? "TRADE",
    tone: j.event === "entry" ? "success" : "info",
    icon: j.event === "entry" ? "entry" : "exit",
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
  pnlPct: number;
  score?: number;
  regime?: string;
};

export function buildTradeOverlays(positions: Position[], journal: JournalEntry[]): TradeOverlay[] {
  return positions.map((p, i) => {
    const j = journal.find((e) => e.event === "entry");
    const stop = typeof j?.fill === "object" && j.fill && "stop_price" in j.fill ? Number(j.fill.stop_price) : undefined;
    const target =
      p.entry > 0 ? p.entry * 1.03 : undefined;
    return {
      id: `${p.asset}-${i}`,
      strategy: p.strategy,
      entry: p.entry,
      current: p.current,
      stop: stop || p.entry * 0.98,
      target,
      pnlPct: p.pnl_pct,
      score: j?.alignment_score ?? undefined,
      regime: j?.regime_label ?? undefined,
    };
  });
}
