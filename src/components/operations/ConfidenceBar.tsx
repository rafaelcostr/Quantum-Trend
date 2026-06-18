export function ConfidenceBar({ value, className = "" }: { value: number; className?: string }) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  const filled = Math.round(pct / 10);
  const blocks = "█".repeat(filled) + "░".repeat(10 - filled);
  const tone = pct >= 85 ? "text-success" : pct >= 60 ? "text-warning" : "text-destructive";
  return (
    <div className={`font-mono text-[11px] ${className}`}>
      <div className={`${tone} tracking-tight`}>{blocks}</div>
      <div className="text-[10px] text-muted-foreground num mt-0.5">{pct}%</div>
    </div>
  );
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div>
      {label && <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">{label}</div>}
      <div className="h-2 rounded-full bg-white/5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${pct >= 80 ? "bg-success" : pct >= 50 ? "bg-warning" : "bg-destructive"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="text-[10px] num text-muted-foreground mt-1 text-right">{pct}%</div>
    </div>
  );
}
