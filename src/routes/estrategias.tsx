import { createFileRoute, Link } from "@tanstack/react-router";
import { PageHeader, Panel } from "@/components/ui/page";
import { useSettings, useStrategies, useUpdateOperational, useUpdateOperationalSlots } from "@/lib/queries";
import type { PaperSlotConfig, OperationalTimeframe } from "@/lib/api";
import { Edit, Copy, Play, MoreHorizontal, Layers } from "lucide-react";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/estrategias")({
  head: () => ({ meta: [{ title: "Estratégias · Quantum-Trend" }] }),
  component: Page,
});

function statusChip(s: string) {
  const map: Record<string, string> = {
    Aprovada: "text-success",
    Demo: "text-secondary",
    Reprovada: "text-destructive",
    Backtest: "text-warning",
    "Sem backtest": "text-muted-foreground",
  };
  return map[s] ?? "text-muted-foreground";
}

const EMPTY_SLOT = (strategy = "mm200_trend_v2"): PaperSlotConfig => ({
  strategy,
  timeframe: "4h",
  quote: "USDT",
  enabled: false,
});

function Page() {
  const { data, isPending, error, isError } = useStrategies();
  const settings = useSettings();
  const activate = useUpdateOperational();
  const saveSlots = useUpdateOperationalSlots();
  const [timeframe, setTimeframe] = useState<OperationalTimeframe>("4h");
  const [msg, setMsg] = useState<string | null>(null);
  const [slots, setSlots] = useState<PaperSlotConfig[]>([
    EMPTY_SLOT(),
    EMPTY_SLOT(),
    EMPTY_SLOT(),
  ]);

  const strategies = settings.data?.operational?.strategies ?? [];
  const maxSlots = settings.data?.operational?.max_slots ?? 3;
  const botRunning = settings.data?.system.bot_running;

  useEffect(() => {
    const saved = settings.data?.operational?.slots;
    if (!saved?.length) return;
    const next: PaperSlotConfig[] = [];
    for (let i = 0; i < 3; i++) {
      const s = saved[i];
      next.push(
        s
          ? { strategy: s.strategy, timeframe: s.timeframe as OperationalTimeframe, quote: s.quote, enabled: s.enabled }
          : EMPTY_SLOT(),
      );
    }
    setSlots(next);
  }, [settings.data?.operational?.slots]);

  if (!isPending && (isError || !data)) {
    return <div className="text-destructive text-sm">Erro ao carregar estratégias.</div>;
  }
  if (isPending || !data) {
    return <div className="text-muted-foreground text-sm">Carregando estratégias…</div>;
  }

  const activeId = settings.data?.system.strategy_id;
  const enabledCount = slots.filter((s) => s.enabled).length;

  const onActivate = (strategyId: string) => {
    setMsg(null);
    activate.mutate(
      { strategy: strategyId, timeframe },
      {
        onSuccess: () => setMsg(`Slot 1 atualizado: ${strategyId} · ${timeframe.toUpperCase()} — salve slots ou inicie o bot.`),
        onError: (e) => setMsg(e instanceof Error ? e.message : "Erro ao ativar"),
      },
    );
  };

  const onSaveSlots = () => {
    setMsg(null);
    saveSlots.mutate(slots.slice(0, maxSlots), {
      onSuccess: () =>
        setMsg(
          enabledCount === 0
            ? "Slots salvos — habilite ao menos 1 antes de iniciar o bot."
            : `${enabledCount} estratégia(s) pronta(s) — clique Iniciar Paper no Dashboard.`,
        ),
      onError: (e) => setMsg(e instanceof Error ? e.message : "Erro ao salvar slots"),
    });
  };

  const updateSlot = (index: number, patch: Partial<PaperSlotConfig>) => {
    setSlots((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Estratégias"
        subtitle="Configure até 3 estratégias em paralelo — mix 1H, 4H e 1D no mesmo bot paper."
        actions={
          <Link to="/backtests" className="rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10">
            Backtests
          </Link>
        }
      />

      {msg && <p className="text-sm text-secondary">{msg}</p>}
      {botRunning && (
        <p className="text-sm text-warning">Pare o bot antes de alterar slots ou estratégias.</p>
      )}

      <Panel title="Operação paralela (até 3)" subtitle="Marque as combinações estratégia + timeframe que rodam juntas na demo.">
        <div className="space-y-3">
          {slots.slice(0, maxSlots).map((slot, i) => (
            <div
              key={i}
              className={`flex flex-wrap items-center gap-3 rounded-xl border px-4 py-3 ${
                slot.enabled ? "border-primary/30 bg-primary/5" : "border-white/5 bg-white/[0.02]"
              }`}
            >
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={slot.enabled}
                  disabled={botRunning}
                  onChange={(e) => updateSlot(i, { enabled: e.target.checked })}
                  className="rounded border-white/20"
                />
                <span className="text-muted-foreground w-14">Slot {i + 1}</span>
              </label>
              <select
                value={slot.strategy}
                disabled={botRunning}
                onChange={(e) => updateSlot(i, { strategy: e.target.value })}
                className="flex-1 min-w-[180px] rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white"
              >
                {strategies.map((s) => (
                  <option key={s.id} value={s.id} className="text-black bg-white">{s.name}</option>
                ))}
              </select>
              <select
                value={slot.timeframe}
                disabled={botRunning}
                onChange={(e) => updateSlot(i, { timeframe: e.target.value as OperationalTimeframe })}
                className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm w-24 text-white"
              >
                <option value="1h" className="text-black bg-white">1H</option>
                <option value="4h" className="text-black bg-white">4H</option>
                <option value="1d" className="text-black bg-white">1D</option>
              </select>
              {slot.enabled && (
                <span className="text-xs text-success flex items-center gap-1">
                  <Layers className="h-3 w-3" />
                  {slot.timeframe.toUpperCase()}
                </span>
              )}
            </div>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onSaveSlots}
            disabled={saveSlots.isPending || botRunning}
            className="rounded-xl bg-gradient-to-r from-[#7C3AED] to-[#3B82F6] px-5 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Salvar configuração
          </button>
          <span className="text-xs text-muted-foreground">
            {enabledCount} de {maxSlots} habilitada(s) · reinicie o bot após salvar
          </span>
        </div>
      </Panel>

      <Panel title="Ranking de backtests" subtitle="Clique ▶ para definir slot 1 rapidamente (1H, 4H ou 1D do seletor ao lado).">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[11px] uppercase tracking-wider text-muted-foreground">
              <tr className="text-left">
                <th className="px-3 py-2 font-medium">Nome</th>
                <th className="px-3 py-2 font-medium text-right">Win Rate</th>
                <th className="px-3 py-2 font-medium text-right">Profit Factor</th>
                <th className="px-3 py-2 font-medium text-right">Drawdown</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium text-right">Ações</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((s) => {
                const sid = s.id || s.name;
                const isActive = activeId === sid;
                const inSlots = slots.some((sl) => sl.enabled && sl.strategy === sid);
                return (
                  <tr key={sid} className={`border-t border-white/5 hover:bg-white/[0.03] transition ${isActive || inSlots ? "bg-primary/5" : ""}`}>
                    <td className="px-3 py-3">
                      <div className="font-medium">{s.name}</div>
                      <div className="text-[11px] text-muted-foreground">
                        {sid}
                        {inSlots ? " · em slot paralelo" : isActive ? ` · slot 1 · ${settings.data?.system.timeframe?.toUpperCase()}` : ""}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-right num">{s.winrate.toFixed(1)}%</td>
                    <td className="px-3 py-3 text-right num">{s.pf.toFixed(2)}</td>
                    <td className="px-3 py-3 text-right num">{s.dd.toFixed(1)}%</td>
                    <td className="px-3 py-3"><span className={`chip ${statusChip(s.status)}`}>{s.status}</span></td>
                    <td className="px-3 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <select
                          value={timeframe}
                          onChange={(e) => setTimeframe(e.target.value as OperationalTimeframe)}
                          className="mr-1 rounded-lg bg-white/5 border border-white/10 px-2 py-1 text-xs text-white"
                          title="Timeframe para slot 1"
                        >
                          <option value="1h" className="text-black bg-white">1H</option>
                          <option value="4h" className="text-black bg-white">4H</option>
                          <option value="1d" className="text-black bg-white">1D</option>
                        </select>
                        <button
                          title={`Definir slot 1 · ${timeframe.toUpperCase()}`}
                          disabled={activate.isPending || botRunning}
                          onClick={() => onActivate(sid)}
                          className="h-8 w-8 grid place-items-center rounded-lg hover:bg-white/10 disabled:opacity-40"
                        >
                          <Play className="h-3.5 w-3.5" />
                        </button>
                        <button className="h-8 w-8 grid place-items-center rounded-lg hover:bg-white/10 opacity-40" disabled><Edit className="h-3.5 w-3.5" /></button>
                        <button className="h-8 w-8 grid place-items-center rounded-lg hover:bg-white/10 opacity-40" disabled><Copy className="h-3.5 w-3.5" /></button>
                        <button className="h-8 w-8 grid place-items-center rounded-lg hover:bg-white/10 opacity-40" disabled><MoreHorizontal className="h-3.5 w-3.5" /></button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
