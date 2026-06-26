import type { BacktestAllProgress, OperatedBase } from "@/lib/api";
import { resolveRunningAsset, resolveRunningLabel } from "@/lib/backtest-running";

const ASSET_STYLE: Record<OperatedBase, { bg: string; border: string; dot: string; label: string }> = {
  BTC: {
    bg: "from-[#F7931A]/20 to-transparent",
    border: "border-[#F7931A]/40",
    dot: "#F7931A",
    label: "Bitcoin",
  },
  ETH: {
    bg: "from-[#627EEA]/20 to-transparent",
    border: "border-[#627EEA]/40",
    dot: "#627EEA",
    label: "Ethereum",
  },
};

export function BacktestRunningBanner({
  progress,
  totalFallback = 45,
}: {
  progress: BacktestAllProgress | null | undefined;
  totalFallback?: number;
}) {
  if (!progress || progress.status !== "running") return null;

  const base = (resolveRunningAsset(progress) ?? "BTC") as OperatedBase;
  const style = ASSET_STYLE[base];
  const label = resolveRunningLabel(progress) ?? `${base}/USDT`;
  const total = progress.total || totalFallback;
  const pct = total > 0 ? Math.max(4, Math.min(100, Math.round((progress.completed / total) * 100))) : 4;

  return (
    <div
      className={`mt-4 space-y-3 rounded-xl border ${style.border} bg-gradient-to-br ${style.bg} to-white/[0.02] p-4`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span
            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs font-semibold uppercase tracking-wide"
          >
            <span className="h-2.5 w-2.5 rounded-full animate-pulse" style={{ backgroundColor: style.dot }} />
            Testando {label}
          </span>
          <span className="text-sm text-white font-medium">{style.label}</span>
        </div>
        <span className="num text-sm text-muted-foreground">
          {progress.completed}/{total}
        </span>
      </div>

      <p className="text-sm text-secondary">
        {progress.current ?? "Preparando candles e simulações…"}
      </p>

      <div className="h-2 rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${pct}%`,
            background:
              base === "ETH"
                ? "linear-gradient(to right, #627EEA, #8B5CF6)"
                : "linear-gradient(to right, #F7931A, #FBBF24)",
          }}
        />
      </div>

      <p className="text-[11px] text-muted-foreground">
        Matriz de {total} backtests · mantenha a API Python aberta. Resultados ETH e BTC ficam em abas separadas.
      </p>
    </div>
  );
}
