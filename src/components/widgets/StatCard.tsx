import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

function Sparkline({ data, color, id }: { data: number[]; color: string; id: string }) {
  const values = data.length > 1 ? data : [3, 5, 4, 7, 6, 9, 8, 11, 10, 13];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const points = values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * 100;
      const y = 34 - ((value - min) / span) * 28;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <svg viewBox="0 0 100 40" preserveAspectRatio="none" className="h-12 w-full">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.45} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <polygon points={`0,40 ${points} 100,40`} fill={`url(#${id})`} />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2.5"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export function StatCard({
  label,
  value,
  delta,
  icon: Icon,
  data,
  accent = "primary",
}: {
  label: string;
  value: string;
  delta?: number;
  icon: LucideIcon;
  data?: number[];
  accent?: "primary" | "secondary" | "success" | "warning" | "destructive";
}) {
  const up = (delta ?? 0) >= 0;
  const accentMap = {
    primary: "#7C3AED",
    secondary: "#3B82F6",
    success: "#22C55E",
    warning: "#F59E0B",
    destructive: "#EF4444",
  } as const;
  const color = accentMap[accent];
  const gradId = `g-${label.replace(/\s/g, "")}-${accent}`;

  return (
    <div className="glass rounded-2xl p-5 relative overflow-hidden transition-transform duration-200 hover:-translate-y-0.5">
      <div
        className="absolute -top-12 -right-12 h-32 w-32 rounded-full blur-3xl opacity-30"
        style={{ background: color }}
      />
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs uppercase tracking-wider text-muted-foreground">{label}</span>
        <span
          className="h-8 w-8 grid place-items-center rounded-xl"
          style={{ background: `${color}22`, color }}
        >
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <div className="num text-2xl">{value}</div>
      {delta !== undefined && (
        <div
          className={`mt-1 flex items-center gap-1 text-xs ${up ? "text-success" : "text-destructive"}`}
        >
          {up ? (
            <ArrowUpRight className="h-3.5 w-3.5" />
          ) : (
            <ArrowDownRight className="h-3.5 w-3.5" />
          )}
          {up ? "+" : ""}
          {delta.toFixed(2)}%<span className="text-muted-foreground ml-1">vs ontem</span>
        </div>
      )}
      <div className="h-12 mt-3 -mx-2">
        <Sparkline data={data ?? []} color={color} id={gradId} />
      </div>
    </div>
  );
}
