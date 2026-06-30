import { Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowRight, TrendingDown, TrendingUp, Minus } from "lucide-react";
import { Panel } from "@/components/ui/page";
import { formatApiError, StaleBadge, WarningState } from "@/components/ui/query-state";
import type { MarketRegimeSnapshot } from "@/lib/api";

const REGIME_ICONS = {
  bull: TrendingUp,
  bear: TrendingDown,
  range: Minus,
} as const;

const ACCENT_STYLES = {
  success: {
    badge: "bg-success/15 text-success border-success/30",
    glow: "from-success/20 to-transparent",
  },
  destructive: {
    badge: "bg-destructive/15 text-destructive border-destructive/30",
    glow: "from-destructive/20 to-transparent",
  },
  warning: {
    badge: "bg-warning/15 text-warning border-warning/30",
    glow: "from-warning/20 to-transparent",
  },
} as const;

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white/[0.03] border border-white/5 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-sm font-medium num mt-0.5">{value}</div>
    </div>
  );
}

export function MarketRegimePanel({ regime }: { regime: MarketRegimeSnapshot | undefined }) {
  if (!regime) {
    return (
      <Panel title="Regime de Mercado">
        <p className="text-sm text-muted-foreground">
          Regime indisponível — reinicie a API Python.
        </p>
      </Panel>
    );
  }

  const accent = ACCENT_STYLES[regime.accent] ?? ACCENT_STYLES.warning;
  const Icon = REGIME_ICONS[regime.market_type] ?? Minus;
  const route = regime.strategies_route as
    | "/estrategias-alta"
    | "/estrategias-baixa"
    | "/estrategias-lateral";

  return (
    <Panel
      title="Regime de Mercado"
      action={
        regime.available ? (
          <div className="flex items-center gap-2">
            <StaleBadge stale={regime.stale} lastSuccessAt={regime.last_success_at} />
            <span className="text-[11px] text-muted-foreground">
              {regime.symbol} · {regime.timeframe.toUpperCase()}
            </span>
          </div>
        ) : null
      }
    >
      {!regime.available ? (
        <div className="text-sm text-muted-foreground space-y-2">
          <p>{regime.reason}</p>
          {regime.error && (
            <p className="text-xs text-destructive/90">{formatApiError(regime.error)}</p>
          )}
        </div>
      ) : (
        <div className="space-y-5">
          {regime.stale && (
            <WarningState>
              <div className="font-medium">Regime usando último dado válido</div>
              <div className="mt-1 text-xs opacity-90">
                A Binance/API falhou na atualização mais recente; a tela manteve o snapshot anterior
                marcado como cacheado.
              </div>
            </WarningState>
          )}

          <div
            className={`relative overflow-hidden rounded-2xl border border-white/10 p-5 bg-gradient-to-br ${accent.glow} to-white/[0.02]`}
          >
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex items-center gap-4">
                <div
                  className={`flex h-14 w-14 items-center justify-center rounded-2xl border ${accent.badge}`}
                >
                  <Icon className="h-7 w-7" />
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-muted-foreground">
                    Tendência sugerida
                  </div>
                  <div className="text-2xl font-semibold">{regime.label}</div>
                  <div className="text-sm text-muted-foreground mt-1 max-w-xl">{regime.reason}</div>
                </div>
              </div>
              <Link
                to={route}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-white/10 border border-white/10 px-4 py-2.5 text-sm font-medium hover:bg-white/15 transition shrink-0"
              >
                Ver{" "}
                {regime.label === "Alta"
                  ? "Estratégias de Alta"
                  : regime.label === "Baixa"
                    ? "Estratégias de Baixa"
                    : "Estratégias Laterais"}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Metric
              label="Preço"
              value={regime.close != null ? `$${regime.close.toLocaleString()}` : "—"}
            />
            <Metric
              label="EMA 200"
              value={regime.ema200 != null ? `$${regime.ema200.toLocaleString()}` : "—"}
            />
            <Metric label="ADX" value={regime.adx != null ? regime.adx.toFixed(1) : "—"} />
            <Metric
              label="vs EMA200"
              value={
                regime.price_vs_ema_pct != null
                  ? `${regime.price_vs_ema_pct >= 0 ? "+" : ""}${regime.price_vs_ema_pct.toFixed(2)}%`
                  : "—"
              }
            />
          </div>

          <div className="rounded-xl bg-white/[0.03] border border-white/5 p-4 text-sm">
            <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
              Recomendação
            </div>
            <p>{regime.suggestion}</p>
            {regime.enabled_slots > 0 && (
              <p className="text-xs text-muted-foreground mt-2">
                Slots paper: {regime.matching_slots}/{regime.enabled_slots} compatíveis com o regime
                atual
                {regime.active_market_labels.length > 0 && (
                  <> · ativos: {regime.active_market_labels.join(", ")}</>
                )}
              </p>
            )}
          </div>

          {regime.warning && (
            <div className="flex items-start gap-2 rounded-xl border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
              <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
              <div>
                <div className="font-medium">Slots não alinhados ao mercado</div>
                <div className="text-xs mt-1 opacity-90">{regime.warning}</div>
              </div>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
