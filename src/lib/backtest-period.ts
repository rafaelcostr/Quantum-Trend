export type BacktestPeriodFields = {
  period_start?: string | null;
  period_end?: string | null;
  period_days?: number | null;
};

function formatDuration(days: number | null | undefined): string {
  if (!days || days < 1) return "";
  if (days >= 730) {
    const years = days / 365.25;
    return years >= 10 ? `~${Math.round(years)} anos` : `~${years.toFixed(1)} anos`;
  }
  if (days >= 60) return `~${Math.round(days / 30.4)} meses`;
  return `${days} dias`;
}

/** Formato compacto para tabelas: 2017-08 → 2025-06 (~7.8 anos) */
export function formatBacktestPeriodShort(p?: BacktestPeriodFields | null): string {
  if (!p?.period_start || !p?.period_end) return "—";
  const start = p.period_start.slice(0, 7);
  const end = p.period_end.slice(0, 7);
  const duration = formatDuration(p.period_days ?? null);
  return duration ? `${start} → ${end} (${duration})` : `${start} → ${end}`;
}

/** Formato longo para detalhe: Período simulado: 2017-08-17 → 2025-06-01 (~7.8 anos) */
export function formatBacktestPeriodLong(p?: BacktestPeriodFields | null): string | null {
  if (!p?.period_start || !p?.period_end) return null;
  const duration = formatDuration(p.period_days ?? null);
  return `Período simulado: ${p.period_start} → ${p.period_end}${duration ? ` (${duration})` : ""}`;
}

/** Trades com contexto de tempo: 378 trades · ~7.8 anos */
export function formatTradesWithPeriod(
  trades: number,
  p?: BacktestPeriodFields | null,
): string {
  if (trades === 0) return "0";
  const duration = formatDuration(p?.period_days ?? null);
  return duration ? `${trades} · ${duration}` : String(trades);
}
