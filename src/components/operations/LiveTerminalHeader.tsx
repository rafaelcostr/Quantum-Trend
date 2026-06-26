import type { ReactNode } from "react";
import { Activity, Clock, DollarSign, Gauge, Layers, Radio, Timer, TrendingUp, Wifi, Zap } from "lucide-react";
import type { BotStatus, DashboardStats, PlatformStatus, QuantumStatus } from "@/lib/api";
import {
  botHeaderLabel,
  exchangeLabel,
  fmtCountdown,
  inferRegime,
  type HeaderMetrics,
} from "@/lib/operations-terminal";
import { BotUptimeTimer } from "./BotUptimeTimer";

type Props = {
  stats: DashboardStats;
  bot: BotStatus;
  mode: string;
  symbol: string;
  timeframe: string;
  quantum?: QuantumStatus;
  platform?: PlatformStatus;
  metrics: HeaderMetrics;
  isStreaming: boolean;
};

export function LiveTerminalHeader({
  stats,
  bot,
  mode,
  symbol,
  timeframe,
  quantum,
  platform,
  metrics,
  isStreaming,
}: Props) {
  const running = bot.running;
  const regime = inferRegime(quantum?.last_reason, quantum, platform);
  const alignment = stats.alignment_score || platform?.alignment_score || quantum?.alignment_score || 0;
  const health = stats.health_score || platform?.system_health || quantum?.health_score || 0;

  const chips: {
    icon: typeof Radio;
    label: string;
    value: ReactNode;
    tone?: string;
  }[] = [
    {
      icon: Radio,
      label: "Bot",
      value: botHeaderLabel(bot, mode),
      tone: running && !bot.last_error ? "text-success" : bot.last_error ? "text-destructive" : "text-muted-foreground",
    },
    { icon: Activity, label: "Exchange", value: exchangeLabel(stats, mode) },
    { icon: TrendingUp, label: "Ativo", value: symbol.replace("/", "") },
    { icon: Clock, label: "Timeframe", value: timeframe.toUpperCase() },
    { icon: Gauge, label: "Regime", value: regime },
    { icon: Zap, label: "Alignment", value: `${Math.round(alignment)}/100` },
    { icon: Activity, label: "Health", value: `${Math.round(health)}/100` },
    {
      icon: DollarSign,
      label: "Capital",
      value: `$${metrics.capital.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
    },
    { icon: Layers, label: "Posições", value: String(metrics.positions) },
    { icon: Gauge, label: "Exposição", value: `${metrics.exposurePct}%` },
    {
      icon: Wifi,
      label: "Latência",
      value: metrics.latencyMs != null ? `${metrics.latencyMs}ms` : "—",
    },
    {
      icon: Timer,
      label: "Cronômetro",
      value: <BotUptimeTimer startedAt={bot.started_at} running={running} className="text-sm font-semibold text-success" />,
    },
    {
      icon: Clock,
      label: "Próximo tick",
      value: isStreaming ? "3s (SSE)" : fmtCountdown(metrics.nextTickSec),
    },
  ];

  return (
    <div className="glass rounded-2xl border border-white/10 overflow-hidden">
      <div className="flex items-center justify-between gap-3 px-4 py-2 border-b border-white/5 bg-white/[0.02]">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground shrink-0">
            <span className={`h-2 w-2 rounded-full ${running ? "bg-success animate-pulse" : "bg-muted-foreground"}`} />
            Quantum Trend Terminal · Runtime
          </div>
          {running && (
            <div className="hidden sm:flex items-center gap-2 rounded-lg border border-success/25 bg-success/10 px-2.5 py-1 text-xs">
              <Timer className="h-3.5 w-3.5 text-success shrink-0" />
              <BotUptimeTimer startedAt={bot.started_at} running={running} className="text-success font-semibold" showLabel />
            </div>
          )}
        </div>
        <span className={`chip text-[10px] shrink-0 ${mode === "live" ? "text-destructive" : "text-success"}`}>
          {mode === "live" ? "LIVE" : "PAPER"}
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-7 divide-y md:divide-y-0 md:divide-x divide-white/5">
        {chips.map(({ icon: Icon, label, value, tone }) => (
          <div key={label} className="px-4 py-3 min-w-0">
            <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
              <Icon className="h-3 w-3 shrink-0" />
              {label}
            </div>
            <div className={`mt-1 text-sm font-medium truncate num ${tone ?? "text-foreground"}`}>{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
