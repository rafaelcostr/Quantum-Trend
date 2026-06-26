import { useEffect, useState } from "react";
import { fmtUptimeClock } from "@/lib/operations-terminal";

type Props = {
  startedAt: string | null | undefined;
  running: boolean;
  className?: string;
  showLabel?: boolean;
};

export function BotUptimeTimer({ startedAt, running, className = "", showLabel = false }: Props) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!running || !startedAt) return;
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [running, startedAt]);

  if (!running || !startedAt) {
    return <span className={`text-muted-foreground ${className}`}>—</span>;
  }

  return (
    <span className={`inline-flex items-center gap-1.5 font-mono tabular-nums ${className}`}>
      {showLabel && <span className="text-[10px] uppercase tracking-wide text-muted-foreground font-sans">Ligado há</span>}
      <span>{fmtUptimeClock(startedAt, now)}</span>
    </span>
  );
}
