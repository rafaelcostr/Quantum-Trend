import { Activity, Radio } from "lucide-react";
import type { OperationsFeedResponse } from "@/lib/api";

function fmtTime(ts: string | null | undefined) {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts.slice(11, 19);
  }
}

function eventColor(event: string, action?: string | null) {
  if (event === "entry" || action === "entry")
    return "text-success border-success/30 bg-success/10";
  if (event === "exit" || action === "exit")
    return "text-destructive border-destructive/30 bg-destructive/10";
  if (event === "error") return "text-destructive border-destructive/30 bg-destructive/10";
  if (event === "runner_start") return "text-primary border-primary/30 bg-primary/10";
  return "text-muted-foreground border-white/10 bg-white/[0.02]";
}

type Props = {
  data: OperationsFeedResponse;
  compact?: boolean;
};

export function OperationsFeed({ data, compact }: Props) {
  const { items, bot, poll_seconds, next_tick_in, mode } = data;
  const running = bot.running;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <span
          className={`inline-flex items-center gap-1.5 chip ${running ? (mode === "live" ? "text-destructive" : "text-success") : ""}`}
        >
          <Radio className={`h-3 w-3 ${running ? "animate-pulse" : ""}`} />
          {running ? (mode === "live" ? "LIVE" : "PAPER") : "PARADO"}
        </span>
        {running && (
          <>
            <span className="text-muted-foreground">
              Ticks: <span className="num text-foreground">{bot.ticks ?? 0}</span>
            </span>
            <span className="text-muted-foreground">
              Último: <span className="num">{fmtTime(bot.last_tick_at)}</span>
            </span>
            {poll_seconds != null && next_tick_in != null && (
              <span className="text-muted-foreground">
                Próximo tick ~<span className="num">{next_tick_in}s</span>
              </span>
            )}
            {bot.in_position && <span className="chip text-success">Em posição</span>}
          </>
        )}
      </div>

      {!running && (
        <div className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-sm text-muted-foreground">
          <Activity className="h-8 w-8 mx-auto mb-2 opacity-40" />
          Inicie o bot (paper ou live) para ver ticks, sinais e execuções aqui em tempo real.
        </div>
      )}

      <ul className={`space-y-2 ${compact ? "max-h-72" : "max-h-[28rem]"} overflow-y-auto pr-1`}>
        {items.length === 0 && running ? (
          <li className="text-sm text-muted-foreground py-4 text-center">
            Aguardando primeiro tick…
          </li>
        ) : (
          items.map((item, i) => (
            <li
              key={`${item.ts}-${item.event}-${i}`}
              className={`rounded-xl border px-3 py-2.5 text-sm transition-colors ${eventColor(item.event, item.action)}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <span className="text-[10px] uppercase tracking-wider opacity-70">
                    {item.event}
                  </span>
                  <div className="mt-0.5 truncate">{item.message}</div>
                </div>
                <div className="text-right shrink-0 text-[10px] opacity-70">
                  <div>{fmtTime(item.ts)}</div>
                  {item.equity != null && (
                    <div className="num mt-0.5">
                      $
                      {Number(item.equity).toLocaleString(undefined, {
                        maximumFractionDigits: 0,
                      })}
                    </div>
                  )}
                </div>
              </div>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
