import { createFileRoute } from "@tanstack/react-router";
import { PageHeader, Panel } from "@/components/ui/page";
import { useRisk, useUpdateRisk } from "@/lib/queries";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/risco")({
  head: () => ({ meta: [{ title: "Gestão de Risco · Quantum-Trend" }] }),
  component: Page,
});

function Slider({ label, value, min, max, step, suffix, onChange }: {
  label: string; value: number; min: number; max: number; step: number; suffix: string; onChange: (v: number) => void;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <label className="text-sm font-medium">{label}</label>
        <span className="num text-sm text-gradient-primary">{value}{suffix}</span>
      </div>
      <div className="relative h-2 rounded-full bg-white/5">
        <div className="absolute h-full rounded-full bg-gradient-to-r from-[#7C3AED] to-[#3B82F6]" style={{ width: `${pct}%` }} />
        <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(parseFloat(e.target.value))} className="absolute inset-0 w-full opacity-0 cursor-pointer" />
        <div className="absolute -top-1.5 h-5 w-5 rounded-full bg-white border-2 border-[#7C3AED] shadow-lg" style={{ left: `calc(${pct}% - 10px)` }} />
      </div>
    </div>
  );
}

function Page() {
  const { data, isLoading, error } = useRisk();
  const update = useUpdateRisk();
  const [local, setLocal] = useState({
    risk_per_trade_pct: 1, daily_stop_pct: 3, daily_target_pct: 5,
    max_ops_per_day: 20, pause_after_losses: 3, cooldown_minutes: 30,
  });

  useEffect(() => {
    if (data?.settings) {
      setLocal({
        risk_per_trade_pct: data.settings.risk_per_trade_pct,
        daily_stop_pct: data.settings.daily_stop_pct,
        daily_target_pct: data.settings.daily_target_pct,
        max_ops_per_day: data.settings.max_ops_per_day,
        pause_after_losses: data.settings.pause_after_losses,
        cooldown_minutes: data.settings.cooldown_minutes,
      });
    }
  }, [data]);

  const save = (patch: Partial<typeof local>) => {
    const next = { ...local, ...patch };
    setLocal(next);
    update.mutate(next);
  };

  if (isLoading) return <div className="text-muted-foreground text-sm">Carregando risco…</div>;
  if (error || !data) return <div className="text-destructive text-sm">Erro ao carregar gestão de risco.</div>;

  return (
    <div className="space-y-8">
      <PageHeader title="Gestão de Risco" subtitle="Limites do bot paper — sincronizados com o engine Atlas." />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Panel title="Parâmetros" className="lg:col-span-2">
          <div className="space-y-7">
            <Slider label="Risco por operação" value={local.risk_per_trade_pct} min={0.1} max={5} step={0.1} suffix="%" onChange={(v) => save({ risk_per_trade_pct: v })} />
            <Slider label="Stop diário" value={local.daily_stop_pct} min={1} max={10} step={0.5} suffix="%" onChange={(v) => save({ daily_stop_pct: v })} />
            <Slider label="Meta diária" value={local.daily_target_pct} min={1} max={20} step={0.5} suffix="%" onChange={(v) => save({ daily_target_pct: v })} />
            <Slider label="Máximo de operações / dia" value={local.max_ops_per_day} min={1} max={100} step={1} suffix="" onChange={(v) => save({ max_ops_per_day: v })} />
            <Slider label="Pausar após N perdas consecutivas" value={local.pause_after_losses} min={1} max={10} step={1} suffix="" onChange={(v) => save({ pause_after_losses: v })} />
            <Slider label="Cooldown automático" value={local.cooldown_minutes} min={5} max={180} step={5} suffix=" min" onChange={(v) => save({ cooldown_minutes: v })} />
          </div>
        </Panel>

        <div className="space-y-6">
          <Panel title="Resumo de Risco">
            <ul className="space-y-3 text-sm">
              <li className="flex justify-between"><span className="text-muted-foreground">Exposição máxima</span><span className="num">${data.summary.max_exposure.toLocaleString()}</span></li>
              <li className="flex justify-between"><span className="text-muted-foreground">Perda máxima diária</span><span className="num text-destructive">-${data.summary.max_daily_loss.toLocaleString()}</span></li>
              <li className="flex justify-between"><span className="text-muted-foreground">Meta diária</span><span className="num text-success">+${data.summary.daily_target.toLocaleString()}</span></li>
              <li className="flex justify-between"><span className="text-muted-foreground">P&L hoje</span><span className="num">${data.settings.daily_pnl.toFixed(2)}</span></li>
            </ul>
          </Panel>
          <Panel title="Proteções Ativas">
            <ul className="space-y-2 text-sm">
              {data.protections.map((p) => (
                <li key={p} className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-success" />{p}</li>
              ))}
            </ul>
          </Panel>
          {data.alert && (
            <Panel title="Alertas">
              <div className="text-xs text-warning">⚠ {data.alert}</div>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
