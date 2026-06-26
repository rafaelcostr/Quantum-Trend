import { Panel } from "@/components/ui/page";
import type { QuantumStatus } from "@/lib/api";

const MODULE_LABELS: Record<string, string> = {
  pullback: "Pullback",
  breakout: "Breakout",
  supertrend: "Supertrend",
};

function ModuleRow({
  name,
  status,
}: {
  name: string;
  status?: { active?: boolean; triggered?: boolean; confidence?: number | null; reason?: string };
}) {
  const label = MODULE_LABELS[name] ?? name;
  const active = status?.active !== false;
  return (
    <div className="flex items-start justify-between gap-3 border-t border-white/5 first:border-t-0 py-3">
      <div>
        <div className="text-sm font-medium">{label}</div>
        <div className="text-[11px] text-muted-foreground mt-0.5">{status?.reason ?? "—"}</div>
      </div>
      <div className="text-right shrink-0">
        <span
          className={`text-xs font-medium ${active ? "text-success" : "text-muted-foreground"}`}
        >
          {active ? "Ativo" : "Inativo"}
        </span>
        {status?.triggered && status.confidence != null && (
          <div className="text-[11px] num text-primary mt-0.5">
            Score {status.confidence.toFixed(0)}
          </div>
        )}
      </div>
    </div>
  );
}

export function QuantumEntryModulesPanel({ quantum }: { quantum: QuantumStatus | undefined }) {
  if (!quantum || quantum.strategy !== "quantum_trend_pro") {
    return null;
  }

  const modules = quantum.module_status ?? {};
  const health = quantum.module_health ?? {};
  const last = quantum.entry_module;
  const stats = quantum.module_backtest_stats ?? {};

  return (
    <Panel title="QuantumTrend Pro · Entry Modules">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">Módulos</p>
          {Object.keys(MODULE_LABELS).map((key) => (
            <ModuleRow key={key} name={key} status={modules[key]} />
          ))}
        </div>

        <div className="space-y-4">
          <div className="rounded-xl bg-white/[0.03] border border-white/5 p-4 text-sm">
            <div className="text-xs text-muted-foreground uppercase mb-2">Último sinal</div>
            {last ? (
              <>
                <div>
                  Módulo: <strong>{MODULE_LABELS[last] ?? last}</strong>
                </div>
                {quantum.entry_confidence != null && (
                  <div className="mt-1">
                    Score:{" "}
                    <span className="num text-primary">{quantum.entry_confidence.toFixed(0)}</span>
                  </div>
                )}
                {quantum.regime_label && (
                  <div className="mt-1 text-muted-foreground">Regime: {quantum.regime_label}</div>
                )}
                <div className="mt-2 text-xs">
                  Resultado:{" "}
                  <span
                    className={
                      quantum.entry_result === "operacao_executada"
                        ? "text-success"
                        : "text-muted-foreground"
                    }
                  >
                    {quantum.entry_result === "operacao_executada"
                      ? "Operação executada"
                      : quantum.entry_result === "detectado_nao_executado"
                        ? "Detectado · não executado"
                        : (quantum.last_reason ?? "Sem sinal")}
                  </span>
                </div>
              </>
            ) : (
              <p className="text-muted-foreground text-sm">Nenhum sinal recente.</p>
            )}
          </div>

          {(Object.keys(health).length > 0 || Object.keys(stats).length > 0) && (
            <div className="rounded-xl bg-white/[0.03] border border-white/5 p-4">
              <div className="text-xs text-muted-foreground uppercase mb-3">Health por módulo</div>
              <div className="space-y-2">
                {Object.entries(health).map(([mod, score]) => (
                  <div key={mod} className="flex justify-between text-sm">
                    <span>{MODULE_LABELS[mod] ?? mod}</span>
                    <span className="num">{score.toFixed(0)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
}
