import { AlertTriangle, CheckCircle2, RefreshCw, Shield, Zap } from "lucide-react";
import { Panel } from "@/components/ui/page";
import type { PlatformStatus } from "@/lib/api";
import { useAckRiskLock } from "@/lib/queries";

function HealthBar({ label, value, max = 100 }: { label: string; value: number; max?: number }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const color = pct >= 80 ? "bg-success" : pct >= 60 ? "bg-warning" : "bg-destructive";
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span className="num font-medium">{value.toFixed(0)}</span>
      </div>
      <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function AlertList({
  title,
  items,
  tone,
}: {
  title: string;
  items: { message: string; ts: string; category?: string }[];
  tone: string;
}) {
  return (
    <div>
      <div className={`text-xs font-semibold uppercase tracking-wide mb-2 ${tone}`}>{title}</div>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">Nenhum alerta.</p>
      ) : (
        <ul className="space-y-2 max-h-40 overflow-y-auto">
          {items.slice(0, 6).map((a, i) => (
            <li key={i} className="text-xs border-l-2 border-white/10 pl-2">
              <div>{a.message}</div>
              <div className="text-[10px] text-muted-foreground mt-0.5">
                {a.ts?.slice(0, 19).replace("T", " ")}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function InstitutionalPanel({ platform }: { platform: PlatformStatus | undefined }) {
  const ackRisk = useAckRiskLock();

  if (!platform) {
    return (
      <Panel title="Plataforma Quantitativa">
        <p className="text-sm text-muted-foreground">
          Dados da plataforma indisponíveis — reinicie a API Python.
        </p>
      </Panel>
    );
  }

  const { runtime, alerts, recovery, data_quality, engine, score_explanation } = platform;
  const groups = alerts.groups;

  return (
    <div className="space-y-6">
      {runtime.risk_locked && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-start gap-2 text-sm text-destructive">
            <Shield className="h-5 w-5 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold">RISK_LOCKED — operações bloqueadas</div>
              <div className="text-xs mt-1 opacity-90">
                {runtime.risk_lock_reason ?? "Inconsistência detectada no recovery."}
              </div>
            </div>
          </div>
          <button
            type="button"
            disabled={ackRisk.isPending}
            onClick={() => ackRisk.mutate()}
            className="rounded-xl bg-destructive px-4 py-2 text-sm font-semibold text-white hover:bg-destructive/90 disabled:opacity-50 shrink-0"
          >
            {ackRisk.isPending ? "Confirmando…" : "Confirmar e liberar"}
          </button>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-2xl bg-white/[0.03] border border-white/5 p-4">
          <div className="text-[11px] text-muted-foreground uppercase">System Health</div>
          <div className="text-2xl font-bold num mt-1">{platform.system_health.toFixed(0)}</div>
        </div>
        <div className="rounded-2xl bg-white/[0.03] border border-white/5 p-4">
          <div className="text-[11px] text-muted-foreground uppercase">Engine Health</div>
          <div className="text-2xl font-bold num mt-1">{platform.engine_health.toFixed(0)}</div>
        </div>
        <div className="rounded-2xl bg-white/[0.03] border border-white/5 p-4">
          <div className="text-[11px] text-muted-foreground uppercase">Data Health</div>
          <div className="text-2xl font-bold num mt-1">{platform.data_health.toFixed(0)}</div>
        </div>
        <div className="rounded-2xl bg-white/[0.03] border border-white/5 p-4">
          <div className="text-[11px] text-muted-foreground uppercase">Estado</div>
          <div className="text-lg font-bold mt-1">{runtime.state}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Panel title="Saúde do Sistema">
          <div className="space-y-4">
            <HealthBar label="Strategy Health" value={platform.strategy_health} />
            <HealthBar label="Engine Health" value={platform.engine_health} />
            <HealthBar label="Data Health" value={platform.data_health} />
            {platform.regime_label && (
              <p className="text-xs text-muted-foreground pt-2">
                Regime: <span className="text-white">{platform.regime_label}</span>
              </p>
            )}
          </div>
        </Panel>

        <Panel title="Runtime">
          <dl className="text-sm space-y-2">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Estado</dt>
              <dd className="font-medium">{runtime.state}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Última sync</dt>
              <dd className="text-xs num">
                {runtime.last_sync?.slice(0, 19).replace("T", " ") ?? "—"}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Próxima análise</dt>
              <dd>{runtime.next_analysis ?? "—"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Latência Binance</dt>
              <dd className="num">
                {engine.binance_latency_ms != null ? `${engine.binance_latency_ms}ms` : "—"}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Broker</dt>
              <dd>{engine.broker_status}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Recovery</dt>
              <dd>{engine.recovery_status}</dd>
            </div>
          </dl>
          {runtime.last_decision && (
            <div className="mt-4 rounded-xl bg-white/[0.03] border border-white/5 p-3">
              <div className="text-[11px] text-muted-foreground uppercase mb-1">Última decisão</div>
              <pre className="text-[11px] whitespace-pre-wrap font-sans text-muted-foreground leading-relaxed max-h-32 overflow-y-auto">
                {runtime.last_decision.narrative ?? runtime.last_decision.outcome}
              </pre>
            </div>
          )}
        </Panel>

        <Panel title="Alert Center">
          <div className="grid grid-cols-1 gap-4">
            <AlertList title="Críticos" items={groups.critical} tone="text-destructive" />
            <AlertList title="Atenção" items={groups.warning} tone="text-warning" />
            <AlertList title="Informativos" items={groups.info} tone="text-secondary" />
          </div>
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Recovery">
          <div className="text-sm space-y-2">
            <div className="flex items-center gap-2">
              {recovery.ok !== false ? (
                <CheckCircle2 className="h-4 w-4 text-success" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-destructive" />
              )}
              <span>
                {recovery.ok !== false ? "Último recovery OK" : "Recovery com inconsistências"}
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              Fonte posição: {recovery.position_source ?? "—"} ·{" "}
              {recovery.reconciled_at?.slice(0, 19).replace("T", " ") ?? "—"}
            </div>
            {(recovery.issues ?? []).length > 0 && (
              <ul className="text-xs text-destructive list-disc pl-4 space-y-1">
                {(recovery.issues as string[]).map((issue, i) => (
                  <li key={i}>{issue}</li>
                ))}
              </ul>
            )}
          </div>
        </Panel>

        <Panel title="Data Quality">
          <div className="text-sm space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Score</span>
              <span className="num font-medium">{data_quality.score?.toFixed(0) ?? "—"}/100</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Candles</span>
              <span>{data_quality.candle_count ?? "—"}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Último candle</span>
              <span className="num">
                {data_quality.last_candle_ts?.slice(0, 16).replace("T", " ") ?? "—"}
              </span>
            </div>
            {(data_quality.issues ?? []).length > 0 && (
              <ul className="text-xs text-warning list-disc pl-4 space-y-1 pt-2">
                {(data_quality.issues as string[]).slice(0, 5).map((issue, i) => (
                  <li key={i}>{issue}</li>
                ))}
              </ul>
            )}
          </div>
        </Panel>
      </div>

      {score_explanation && (
        <Panel title="Alignment Score — detalhamento">
          <div className="flex flex-wrap items-baseline gap-2 mb-4">
            <span className="text-2xl font-bold num">{score_explanation.total}</span>
            <span className="text-muted-foreground">
              /100 · mínimo {score_explanation.threshold}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {(score_explanation.components ?? []).map((c) => (
              <div key={c.key} className="rounded-xl bg-white/[0.03] border border-white/5 p-3">
                <div className="text-[11px] text-muted-foreground">{c.label}</div>
                <div className="text-lg font-semibold num">
                  {c.score}/{c.max}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {(platform.capital_scaling?.current_risk_pct != null ||
        platform.trend_exhaustion?.exhausted) && (
        <Panel title="Gestão dinâmica">
          <div className="flex flex-wrap gap-6 text-sm">
            {platform.capital_scaling?.current_risk_pct != null && (
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-warning" />
                <span>
                  Risco atual: <strong>{platform.capital_scaling.current_risk_pct}%</strong> por
                  trade
                </span>
              </div>
            )}
            {platform.trend_exhaustion?.exhausted && (
              <div className="flex items-center gap-2 text-warning">
                <RefreshCw className="h-4 w-4" />
                <span>Exaustão detectada: {platform.trend_exhaustion.reason}</span>
              </div>
            )}
          </div>
        </Panel>
      )}
    </div>
  );
}
