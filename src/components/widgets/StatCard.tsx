import { motion } from "framer-motion";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

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
  const series = (data ?? [3, 5, 4, 7, 6, 9, 8, 11, 10, 13]).map((y, i) => ({ x: i, y }));
  const gradId = `g-${label.replace(/\s/g, "")}-${accent}`;

  return (
    <motion.div
      whileHover={{ y: -3 }}
      transition={{ type: "spring", stiffness: 220, damping: 20 }}
      className="glass rounded-2xl p-5 relative overflow-hidden"
    >
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
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={series}>
            <defs>
              <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.55} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="y"
              stroke={color}
              strokeWidth={2}
              fill={`url(#${gradId})`}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
