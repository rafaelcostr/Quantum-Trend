import { createFileRoute } from "@tanstack/react-router";
import { PageHeader, Panel } from "@/components/ui/page";
import { useJournal } from "@/lib/queries";
import { useState } from "react";
import type { JournalEntry } from "@/lib/api";

export const Route = createFileRoute("/diario")({
  head: () => ({ meta: [{ title: "Journal · Quantum-Trend" }] }),
  component: Page,
});

function label(entry: JournalEntry) {
  if (entry.ts) return String(entry.ts).slice(0, 16).replace("T", " ");
  return entry.date ?? "—";
}

function Page() {
  const { data, isPending, error, isError, isFetching } = useJournal();
  const [sel, setSel] = useState(0);

  if (isPending && !data) return <div className="text-muted-foreground text-sm">Carregando journal…</div>;
  if ((isError && !data) || !data || data.items.length === 0) {
    return <div className="text-muted-foreground text-sm">Nenhuma operação registrada ainda. Inicie o bot paper para popular o journal automático.</div>;
  }

  const trade = data.items[sel] ?? data.items[0];
  const enriched = Boolean(trade.reason || trade.alignment_score != null);

  return (
    <div className="space-y-8">
      <PageHeader title="Journal Automático" subtitle="Horário, motivo, score, regime e indicadores no momento da operação." />
      {isFetching && (
        <p className="text-xs text-muted-foreground">Atualizando entradas…</p>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Panel className="xl:col-span-2">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr className="text-left">
                  <th className="px-3 py-2 font-medium">Horário</th>
                  <th className="px-3 py-2 font-medium">Evento</th>
                  <th className="px-3 py-2 font-medium">Motivo</th>
                  <th className="px-3 py-2 font-medium text-right">Score</th>
                  <th className="px-3 py-2 font-medium">Regime</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((t, i) => (
                  <tr
                    key={i}
                    onClick={() => setSel(i)}
                    className={`border-t border-white/5 cursor-pointer transition ${i === sel ? "bg-primary/10" : "hover:bg-white/[0.03]"}`}
                  >
                    <td className="px-3 py-3 text-xs text-muted-foreground">{label(t)}</td>
                    <td className="px-3 py-3 font-medium uppercase text-xs">{t.event ?? (t.pnl != null ? "trade" : "—")}</td>
                    <td className="px-3 py-3 text-muted-foreground max-w-xs truncate">{t.reason ?? t.strategy ?? "—"}</td>
                    <td className="px-3 py-3 text-right num">{t.alignment_score != null ? t.alignment_score.toFixed(0) : "—"}</td>
                    <td className="px-3 py-3 text-xs">{t.regime_label ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Detalhes da Operação">
          <div className="mt-4 space-y-3 text-sm">
            <Row label="Horário" value={label(trade)} />
            <Row label="Evento" value={trade.event ?? "—"} />
            <Row label="Motivo" value={trade.reason ?? trade.strategy ?? "—"} />
            {trade.alignment_score != null && <Row label="Alignment Score" value={trade.alignment_score.toFixed(1)} />}
            {trade.regime_label && <Row label="Regime" value={trade.regime_label} />}
            {trade.entry_module && <Row label="Módulo" value={trade.entry_module} />}
            {!enriched && trade.pnl != null && (
              <Row label="P&L" value={`${trade.pnl >= 0 ? "+" : ""}$${trade.pnl.toFixed(2)}`} />
            )}
            {trade.indicators && (
              <pre className="mt-4 rounded-xl bg-black/30 p-3 text-[10px] overflow-auto max-h-48 text-muted-foreground">
                {JSON.stringify(trade.indicators, null, 2)}
              </pre>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Row({ label: l, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-muted-foreground">{l}</span>
      <span className="font-medium text-right">{value}</span>
    </div>
  );
}
