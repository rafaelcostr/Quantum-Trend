import { Activity, Clock, Gauge, Radio, TrendingUp, Zap } from "lucide-react";
import type { BotStatus, DashboardStats, PlatformStatus, QuantumStatus } from "@/lib/api";
import { botHeaderLabel, exchangeLabel, fmtCountdown, inferRegime } from "@/lib/operations-terminal";

type Props = {
  stats: DashboardStats;
  bot: BotStatus;
  mode: string;
  symbol: string;
  timeframe: string;
  quantum?: QuantumStatus;
  platform?: PlatformStatus;
  nextUpdateSec: number | null;
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
  nextUpdateSec,
  isStreaming,
}: Props) {
  const running = bot.running;
  const regime = inferRegime(stats.bot_phase, quantum, platform);
  const alignment = stats.alignment_score || platform?.alignment_score || quantum?.alignment_score || 0;
  const health = stats.health_score || platform?.system_health || quantum?.health_score || 0;

  const chips = [
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
    { icon: Clock, label: "Próxima atualização", value: isStreaming ? "3s (SSE)" : fmtCountdown(nextUpdateSec) },
  ];

  return (
    <div className="glass rounded-2xl border border-white/10 overflow-hidden">
      <div className="flex items-center justify-between gap-3 px-4 py-2 border-b border-white/5 bg-white/[0.02]">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          <span className={`h-2 w-2 rounded-full ${running ? "bg-success animate-pulse" : "bg-muted-foreground"}`} />
          Quantum Trend Terminal · Runtime
        </div>
        <span className={`chip text-[10px] ${mode === "live" ? "text-destructive" : "text-success"}`}>
          {mode === "live" ? "LIVE" : "PAPER"}
        </span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 divide-y md:divide-y-0 md:divide-x divide-white/5">
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
