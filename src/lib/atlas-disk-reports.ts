import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";

type ReportMetrics = {
  total_return_pct: number;
  profit_factor: number;
  max_drawdown_pct: number;
  sharpe: number;
  win_rate_pct: number;
  trades: number;
  expectancy: number;
  atlas_score: number;
};

type MatrixItem = {
  strategy: string;
  strategy_label: string;
  timeframe: string;
  base_asset?: "BTC" | "ETH";
  period_start?: string | null;
  period_end?: string | null;
  period_days?: number | null;
  ok: boolean;
  report_path: string;
  result: "lucro" | "prejuizo" | "empate";
  metrics: ReportMetrics;
};

const STRATEGY_LABELS: Record<string, string> = {
  mm200_trend_v1: "MM200 Trend v1",
  mm200_trend_v2: "MM200 Trend v2",
  mm200_daily_macro_v1: "MM200 Daily Macro v1",
  range_hunter_v1: "Range Hunter v1",
  range_hunter_v2: "Range Hunter v2",
  bb_squeeze_v1: "BB Squeeze v1",
  regime_switching_v1: "Regime Switching v1",
  portfolio_macro_micro_v1: "Portfolio Macro/Micro v1",
  pullback_ema20_v1: "Pullback EMA20 v1",
  breakout_high20_v1: "Breakout High20 v1",
  supertrend_mm200_v1: "Supertrend + EMA200 v1",
};

function strategyLabel(id: string): string {
  return STRATEGY_LABELS[id] ?? id.replace(/_/g, " ");
}

function parseReportStem(
  stem: string,
): { strategy: string; timeframe: string; quote: string; base_asset: "BTC" | "ETH" } | null {
  const m = stem.match(/^(.+)_(4h|1d|1h)_(usdt|usdc)(?:_(btc|eth))?(?:_report)?$/i);
  if (!m) return null;
  const base = (m[4]?.toUpperCase() ?? "BTC") as "BTC" | "ETH";
  return {
    strategy: m[1],
    timeframe: m[2].toLowerCase(),
    quote: m[3].toUpperCase(),
    base_asset: base,
  };
}

function round(n: number, d: number): number {
  if (!Number.isFinite(n)) return 0;
  const p = 10 ** d;
  return Math.round(n * p) / p;
}

function normalizeReturnPct(stats: Record<string, unknown>): number {
  const raw = Number(stats.net_profit_pct ?? stats.total_return_pct ?? 0);
  return round(Math.abs(raw) <= 1 ? raw * 100 : raw, 2);
}

function normalizeDrawdownPct(stats: Record<string, unknown>): number {
  const raw = Number(stats.max_drawdown_pct ?? 0);
  return round(Math.abs(raw) <= 1 ? raw * 100 : raw, 2);
}

function metricsFromRaw(raw: Record<string, unknown>): ReportMetrics {
  const stats = (raw.statistics ?? raw.metrics ?? {}) as Record<string, unknown>;
  const winRate = Number(stats.win_rate ?? 0);
  return {
    total_return_pct: normalizeReturnPct(stats),
    profit_factor: round(Number(stats.profit_factor ?? 0), 2),
    max_drawdown_pct: normalizeDrawdownPct(stats),
    sharpe: round(Number(stats.sharpe_ratio ?? stats.sharpe ?? 0), 2),
    win_rate_pct: round(winRate <= 1 ? winRate * 100 : winRate, 2),
    trades: Number(stats.total_trades ?? stats.trades ?? 0),
    expectancy: round(Number(stats.avg_trade_pct ?? stats.expectancy ?? 0), 4),
    atlas_score: round(
      Number((raw.metrics as Record<string, unknown> | undefined)?.atlas_score ?? 0),
      1,
    ),
  };
}

type ParsedTrade = {
  exit_time: string;
  pnl: number;
  pnl_pct: number;
};

const MONTH_LABELS = [
  "Jan",
  "Fev",
  "Mar",
  "Abr",
  "Mai",
  "Jun",
  "Jul",
  "Ago",
  "Set",
  "Out",
  "Nov",
  "Dez",
];

function monthLabel(isoTs: string): string {
  const d = new Date(isoTs);
  if (Number.isNaN(d.getTime())) return "—";
  return MONTH_LABELS[d.getUTCMonth()] ?? "—";
}

function tradeFromReportRow(raw: Record<string, unknown>): ParsedTrade {
  const rawPct = Number(raw.pnl_pct ?? 0);
  const pnlPct = Math.abs(rawPct) <= 1 ? rawPct * 100 : rawPct;
  return {
    exit_time: String(raw.exit_time ?? ""),
    pnl: Number(raw.pnl ?? 0),
    pnl_pct: pnlPct,
  };
}

function monthlyReturnsFromEquity(equityRaw: unknown[]): { m: string; r: number }[] {
  if (!equityRaw.length) return [];
  const byMonth = new Map<string, number[]>();
  for (const row of equityRaw) {
    const r = row as Record<string, unknown>;
    const ts = String(r.timestamp ?? r.day ?? "");
    if (ts.length < 7) continue;
    const ym = ts.slice(0, 7);
    const list = byMonth.get(ym) ?? [];
    list.push(Number(r.equity ?? 0));
    byMonth.set(ym, list);
  }

  const out: { m: string; r: number }[] = [];
  let prevEnd: number | null = null;
  for (const ym of [...byMonth.keys()].sort()) {
    const points = byMonth.get(ym)!;
    const start = prevEnd ?? points[0];
    const end = points[points.length - 1];
    if (!start) continue;
    const retPct = (end / start - 1) * 100;
    const [, monthNum] = ym.split("-");
    const year = ym.slice(2, 4);
    const label = `${MONTH_LABELS[Number(monthNum) - 1]}/${year}`;
    out.push({ m: label, r: round(retPct, 1) });
    prevEnd = end;
  }
  return out;
}

function monthlyReturnsFromTrades(
  trades: ParsedTrade[],
  initial = 10000,
): { m: string; r: number }[] {
  if (!trades.length) return [];
  const buckets = new Map<string, number>();
  let equity = initial;
  for (const t of trades) {
    const month = monthLabel(t.exit_time);
    const retPct = equity ? (t.pnl / equity) * 100 : 0;
    buckets.set(month, round((buckets.get(month) ?? 0) + retPct, 1));
    equity += t.pnl;
  }
  return [...buckets.entries()].map(([m, r]) => ({ m, r }));
}

function tradeDistribution(trades: ParsedTrade[]): { bucket: string; n: number }[] {
  const buckets: Record<string, number> = {
    "<-5%": 0,
    "-5..-2": 0,
    "-2..0": 0,
    "0..2": 0,
    "2..5": 0,
    ">5%": 0,
  };
  for (const t of trades) {
    const pct = t.pnl_pct;
    if (pct < -5) buckets["<-5%"] += 1;
    else if (pct < -2) buckets["-5..-2"] += 1;
    else if (pct < 0) buckets["-2..0"] += 1;
    else if (pct < 2) buckets["0..2"] += 1;
    else if (pct < 5) buckets["2..5"] += 1;
    else buckets[">5%"] += 1;
  }
  return Object.entries(buckets).map(([bucket, n]) => ({ bucket, n }));
}

function periodFromEquity(equityRaw: unknown[]): {
  period_start: string | null;
  period_end: string | null;
  days: number | null;
} {
  if (!equityRaw.length) return { period_start: null, period_end: null, days: null };
  const first = equityRaw[0] as Record<string, unknown>;
  const last = equityRaw[equityRaw.length - 1] as Record<string, unknown>;
  const startTs = String(first.timestamp ?? first.day ?? "").slice(0, 10);
  const endTs = String(last.timestamp ?? last.day ?? "").slice(0, 10);
  if (!startTs || !endTs) return { period_start: null, period_end: null, days: null };
  const start = new Date(`${startTs}T00:00:00Z`);
  const end = new Date(`${endTs}T00:00:00Z`);
  const days =
    Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())
      ? null
      : Math.max(1, Math.round((end.getTime() - start.getTime()) / 86_400_000));
  return { period_start: startTs, period_end: endTs, days };
}

async function reportsDir(): Promise<string> {
  return join(process.cwd(), "data", "reports");
}

async function loadReportFile(filename: string): Promise<Record<string, unknown>> {
  const raw = await readFile(join(await reportsDir(), filename), "utf8");
  return JSON.parse(raw) as Record<string, unknown>;
}

export async function buildMatrixFromDisk(quote = "USDT"): Promise<{
  total: number;
  quote: string;
  best_return: MatrixItem | null;
  best_score: MatrixItem | null;
  items: MatrixItem[];
}> {
  const dir = await reportsDir();
  const files = (await readdir(dir))
    .filter((f) => f.endsWith(".json") && !f.toLowerCase().includes("walkforward"))
    .sort();
  const items: MatrixItem[] = [];

  for (const file of files) {
    const parsed = parseReportStem(file.replace(/\.json$/, ""));
    if (!parsed || parsed.quote !== quote.toUpperCase()) continue;
    try {
      const raw = await loadReportFile(file);
      const metrics = metricsFromRaw(raw);
      const equityRaw = Array.isArray(raw.equity_curve) ? raw.equity_curve : [];
      const meta = (raw.metadata ?? {}) as Record<string, unknown>;
      const baseFromMeta = String(meta.base_asset ?? "").toUpperCase();
      const base_asset = (baseFromMeta === "ETH" ? "ETH" : parsed.base_asset) as "BTC" | "ETH";
      const period = periodFromEquity(equityRaw);
      const ret = metrics.total_return_pct;
      items.push({
        strategy: parsed.strategy,
        strategy_label: strategyLabel(parsed.strategy),
        timeframe: parsed.timeframe,
        base_asset,
        period_start: period.period_start,
        period_end: period.period_end,
        period_days: period.days,
        ok: true,
        report_path: join(dir, file),
        result: ret > 0 ? "lucro" : ret < 0 ? "prejuizo" : "empate",
        metrics,
      });
    } catch {
      /* skip broken file */
    }
  }

  items.sort((a, b) => (b.metrics.total_return_pct ?? 0) - (a.metrics.total_return_pct ?? 0));
  const byScore = [...items].sort(
    (a, b) => (b.metrics.atlas_score ?? 0) - (a.metrics.atlas_score ?? 0),
  );

  return {
    total: items.length,
    quote: quote.toUpperCase(),
    best_return: items[0] ?? null,
    best_score: byScore[0] ?? null,
    items,
  };
}

export async function buildResultsFromDisk(
  strategy: string,
  timeframe: string,
  quote = "USDT",
  baseAsset: "BTC" | "ETH" = "BTC",
) {
  const base = baseAsset.toLowerCase();
  const candidates = [
    `${strategy}_${timeframe.toLowerCase()}_${quote.toLowerCase()}_${base}_report.json`,
    `${strategy}_${timeframe.toLowerCase()}_${quote.toLowerCase()}_${base}.json`,
    `${strategy}_${timeframe.toLowerCase()}_${quote.toLowerCase()}_report.json`,
  ];
  let raw: Record<string, unknown> | null = null;
  for (const file of candidates) {
    try {
      raw = await loadReportFile(file);
      break;
    } catch {
      /* try next */
    }
  }
  if (!raw)
    throw new Error(`Relatório não encontrado para ${strategy} · ${timeframe} · ${baseAsset}`);
  const metrics = metricsFromRaw(raw);
  const meta = (raw.metadata ?? {}) as Record<string, unknown>;
  const symbol = String(meta.market ?? "BTC/USDT");
  const tradesRaw = Array.isArray(raw.trades) ? raw.trades : [];
  const equityRaw = Array.isArray(raw.equity_curve) ? raw.equity_curve : [];
  const parsedTrades = tradesRaw.map((t) => tradeFromReportRow(t as Record<string, unknown>));
  const period = periodFromEquity(equityRaw);

  const equity_curve = equityRaw.slice(-120).map((row) => {
    const r = row as Record<string, unknown>;
    const ts = String(r.timestamp ?? r.day ?? "");
    return { day: ts.slice(0, 10) || ts || "—", equity: round(Number(r.equity ?? 0), 2) };
  });

  return {
    title: `${strategyLabel(strategy)} · ${symbol} · ${timeframe.toLowerCase()}`,
    strategy,
    timeframe: timeframe.toLowerCase(),
    metrics,
    equity_curve,
    monthly_returns: monthlyReturnsFromEquity(equityRaw),
    distribution: tradeDistribution(parsedTrades),
    period_start: period.period_start,
    period_end: period.period_end,
    period_days: period.days,
    spark_up: equity_curve.map((e) => e.equity),
    spark_mix: equity_curve.map((e) => e.equity),
  };
}

export function isResultsPath(apiPath: string): { strategy: string; timeframe: string } | null {
  const m = apiPath.match(/^\/api\/results\/([^/]+)\/([^/]+)$/);
  if (!m) return null;
  return { strategy: decodeURIComponent(m[1]), timeframe: decodeURIComponent(m[2]) };
}

export function isMatrixPath(apiPath: string): boolean {
  return apiPath === "/api/backtest/matrix";
}
