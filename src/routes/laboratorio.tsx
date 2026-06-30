import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { BookOpenCheck, Check, GitCompare, PlayCircle, Save, Tags } from "lucide-react";
import { PageHeader, Panel } from "@/components/ui/page";
import { EmptyState, InlineError, LoadingBlock } from "@/components/ui/query-state";
import {
  useQuantLabComparison,
  useQuantLabExperiments,
  useQuantLabReplay,
  useQuantLabStrategies,
  useUpdateQuantLabAnnotation,
  useUpdateQuantLabStrategyStatus,
} from "@/lib/queries";
import type {
  QuantLabCurvePoint,
  QuantLabExperiment,
  QuantLabStrategyStatus,
  QuantLabTag,
} from "@/lib/api";

export const Route = createFileRoute("/laboratorio")({
  head: () => ({ meta: [{ title: "Laboratório Quantitativo · Quantum-Trend" }] }),
  component: Page,
});

const SIGNAL_LABEL: Record<string, string> = {
  entry: "Entrada",
  exit: "Saída",
  hold: "Hold",
};

function pct(value: unknown, digits = 2) {
  const num = Number(value ?? 0);
  return Number.isFinite(num) ? `${num.toFixed(digits)}%` : "0.00%";
}

function num(value: unknown, digits = 2) {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? n.toFixed(digits) : "0.00";
}

function MiniCurve({
  points,
  kind = "equity",
}: {
  points: QuantLabCurvePoint[];
  kind?: "equity" | "drawdown";
}) {
  const path = useMemo(() => {
    const values = points
      .map((p) => Number(kind === "equity" ? p.equity : p.drawdown_pct))
      .filter((v) => Number.isFinite(v));
    if (values.length < 2) return "";
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = Math.max(1e-9, max - min);
    return values
      .map((v, i) => {
        const x = (i / Math.max(1, values.length - 1)) * 100;
        const y = 36 - ((v - min) / span) * 32;
        return `${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
      })
      .join(" ");
  }, [kind, points]);

  if (!path) return <div className="h-11 rounded-xl bg-white/5" />;
  return (
    <svg viewBox="0 0 100 40" className="h-11 w-full overflow-visible">
      <path
        d={path}
        fill="none"
        stroke={kind === "equity" ? "rgb(34 197 94)" : "rgb(248 113 113)"}
        strokeWidth="2.25"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function MetricRow({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "good" | "bad";
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-white/5 py-2 text-sm last:border-b-0">
      <span className="text-muted-foreground">{label}</span>
      <span
        className={`num ${tone === "good" ? "text-success" : tone === "bad" ? "text-destructive" : ""}`}
      >
        {value}
      </span>
    </div>
  );
}

function Page() {
  const experiments = useQuantLabExperiments();
  const strategies = useQuantLabStrategies();
  const updateAnnotation = useUpdateQuantLabAnnotation();
  const updateStrategy = useUpdateQuantLabStrategyStatus();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [replayId, setReplayId] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});

  const selectedForCompare = selectedIds.slice(0, 6);
  const comparison = useQuantLabComparison(selectedForCompare);
  const replay = useQuantLabReplay(replayId);
  const items = experiments.data?.items ?? [];
  const selectedReplay = replay.data?.experiment ?? items[0] ?? null;

  const toggleExperiment = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id].slice(-6),
    );
  };

  const toggleTag = (exp: QuantLabExperiment, tag: QuantLabTag) => {
    const tags = exp.tags.includes(tag) ? exp.tags.filter((t) => t !== tag) : [...exp.tags, tag];
    updateAnnotation.mutate({ experimentId: exp.id, tags, note: notes[exp.id] ?? exp.note });
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Laboratório Quantitativo"
        subtitle="Versione experimentos, compare backtests, marque hipóteses e revise o replay candle por candle."
      />

      <Panel
        title="Experimentos Versionados"
        subtitle="Estratégia, parâmetros, timeframe, ativo, período, versão do código e data do teste."
        action={<span className="text-xs text-muted-foreground">{items.length} experimentos</span>}
      >
        {experiments.isLoading && <LoadingBlock label="Carregando experimentos..." />}
        {experiments.isError && (
          <InlineError error={experiments.error} title="Falha ao carregar laboratório" />
        )}
        {!experiments.isLoading && items.length === 0 && (
          <EmptyState
            title="Nenhum experimento salvo"
            detail="Rode backtests para popular data/reports/."
          />
        )}
        {items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-sm">
              <thead className="text-xs uppercase tracking-wide text-muted-foreground">
                <tr className="border-b border-white/10">
                  <th className="py-2 text-left">Comparar</th>
                  <th className="py-2 text-left">Experimento</th>
                  <th className="py-2 text-left">Período</th>
                  <th className="py-2 text-right">Retorno</th>
                  <th className="py-2 text-right">DD</th>
                  <th className="py-2 text-right">Sharpe</th>
                  <th className="py-2 text-left">Tags</th>
                  <th className="py-2 text-left">Nota</th>
                </tr>
              </thead>
              <tbody>
                {items.slice(0, 40).map((exp) => {
                  const active = selectedIds.includes(exp.id);
                  return (
                    <tr key={exp.id} className="border-b border-white/5 align-top">
                      <td className="py-3">
                        <button
                          onClick={() => toggleExperiment(exp.id)}
                          className={`inline-flex h-8 w-8 items-center justify-center rounded-xl border ${
                            active
                              ? "border-primary/60 bg-primary/20 text-white"
                              : "border-white/10 bg-white/5 text-muted-foreground"
                          }`}
                          title="Selecionar para comparação"
                        >
                          {active && <Check className="h-4 w-4" />}
                        </button>
                      </td>
                      <td className="py-3">
                        <button
                          onClick={() => setReplayId(exp.id)}
                          className="text-left font-medium text-white hover:text-primary"
                        >
                          {exp.strategy}
                        </button>
                        <div className="text-xs text-muted-foreground">
                          {exp.asset}/{exp.quote} · {exp.timeframe.toUpperCase()} · v
                          {exp.strategy_version} · código {exp.code_version}
                        </div>
                      </td>
                      <td className="py-3 text-xs text-muted-foreground">
                        {exp.period_start ?? "—"} → {exp.period_end ?? "—"}
                        <div>
                          {exp.period_days ? `${exp.period_days} dias` : "período indefinido"}
                        </div>
                      </td>
                      <td className="py-3 text-right num text-success">
                        {pct(exp.metrics.total_return_pct)}
                      </td>
                      <td className="py-3 text-right num text-destructive">
                        {pct(exp.metrics.max_drawdown_pct)}
                      </td>
                      <td className="py-3 text-right num">{num(exp.metrics.sharpe)}</td>
                      <td className="py-3">
                        <div className="flex max-w-[240px] flex-wrap gap-1.5">
                          {(experiments.data?.allowed_tags ?? []).map((tag) => (
                            <button
                              key={tag}
                              onClick={() => toggleTag(exp, tag)}
                              className={`rounded-full border px-2 py-1 text-[11px] ${
                                exp.tags.includes(tag)
                                  ? "border-secondary/60 bg-secondary/20 text-white"
                                  : "border-white/10 bg-white/5 text-muted-foreground"
                              }`}
                            >
                              {tag}
                            </button>
                          ))}
                        </div>
                      </td>
                      <td className="py-3">
                        <div className="flex min-w-[220px] gap-2">
                          <input
                            value={notes[exp.id] ?? exp.note}
                            onChange={(e) =>
                              setNotes((prev) => ({ ...prev, [exp.id]: e.target.value }))
                            }
                            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs"
                            placeholder="Anotação"
                          />
                          <button
                            onClick={() =>
                              updateAnnotation.mutate({
                                experimentId: exp.id,
                                tags: exp.tags,
                                note: notes[exp.id] ?? exp.note,
                              })
                            }
                            className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/5"
                            title="Salvar anotação"
                          >
                            <Save className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Panel
          className="xl:col-span-2"
          title="Comparação"
          subtitle="Selecione 2 ou mais backtests para comparar equity, drawdown e métricas."
          action={<GitCompare className="h-4 w-4 text-muted-foreground" />}
        >
          {selectedForCompare.length < 2 && (
            <EmptyState title="Selecione experimentos" detail="Marque de 2 a 6 linhas na tabela." />
          )}
          {comparison.isLoading && <LoadingBlock label="Comparando backtests..." />}
          {comparison.isError && (
            <InlineError error={comparison.error} title="Falha na comparação" />
          )}
          {comparison.data && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {comparison.data.equity_curves.map((curve) => (
                  <div
                    key={curve.id}
                    className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
                  >
                    <div className="mb-2 truncate text-xs text-muted-foreground">{curve.label}</div>
                    <MiniCurve points={curve.points} />
                  </div>
                ))}
                {comparison.data.drawdown_curves.map((curve) => (
                  <div
                    key={`${curve.id}-dd`}
                    className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
                  >
                    <div className="mb-2 truncate text-xs text-muted-foreground">
                      Drawdown · {curve.id}
                    </div>
                    <MiniCurve points={curve.points} kind="drawdown" />
                  </div>
                ))}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[680px] text-sm">
                  <thead className="text-xs uppercase text-muted-foreground">
                    <tr className="border-b border-white/10">
                      <th className="py-2 text-left">Ranking</th>
                      <th className="py-2 text-right">Retorno</th>
                      <th className="py-2 text-right">DD</th>
                      <th className="py-2 text-right">Sharpe</th>
                      <th className="py-2 text-right">PF</th>
                      <th className="py-2 text-right">Trades</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.data.ranking.map((row, idx) => {
                      const exp = comparison.data?.experiments.find((e) => e.id === row.id);
                      return (
                        <tr key={row.id} className="border-b border-white/5">
                          <td className="py-2">
                            {idx + 1}. {exp?.strategy ?? row.id}
                          </td>
                          <td className="py-2 text-right num text-success">
                            {pct(row.total_return_pct)}
                          </td>
                          <td className="py-2 text-right num text-destructive">
                            {pct(row.max_drawdown_pct)}
                          </td>
                          <td className="py-2 text-right num">{num(row.sharpe)}</td>
                          <td className="py-2 text-right num">{num(row.profit_factor)}</td>
                          <td className="py-2 text-right num">{row.trades ?? 0}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Panel>

        <Panel
          title="Replay"
          subtitle="Candle por candle com sinal, motivo e indicadores disponíveis no trade."
          action={<PlayCircle className="h-4 w-4 text-muted-foreground" />}
        >
          {!selectedReplay && <EmptyState title="Sem replay" detail="Selecione um experimento." />}
          {selectedReplay && !replayId && (
            <button
              onClick={() => setReplayId(selectedReplay.id)}
              className="mb-4 inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm"
            >
              <PlayCircle className="h-4 w-4" />
              Abrir replay mais recente
            </button>
          )}
          {replay.isLoading && <LoadingBlock label="Montando replay..." />}
          {replay.isError && <InlineError error={replay.error} title="Falha no replay" />}
          {replay.data && (
            <div className="space-y-4">
              <div>
                <div className="font-medium">{replay.data.experiment.strategy}</div>
                <div className="text-xs text-muted-foreground">
                  {replay.data.total_events} candles · {replay.data.total_trades} trades
                </div>
              </div>
              <div className="max-h-[430px] space-y-2 overflow-y-auto pr-1">
                {replay.data.events.slice(0, 120).map((ev) => (
                  <div
                    key={`${ev.index}-${ev.timestamp}`}
                    className="rounded-xl border border-white/10 bg-white/[0.03] p-3"
                  >
                    <div className="flex items-center justify-between gap-2 text-xs">
                      <span className="text-muted-foreground">{ev.timestamp}</span>
                      <span
                        className={`rounded-full px-2 py-0.5 ${
                          ev.signal === "entry"
                            ? "bg-success/15 text-success"
                            : ev.signal === "exit"
                              ? "bg-destructive/15 text-destructive"
                              : "bg-white/5 text-muted-foreground"
                        }`}
                      >
                        {SIGNAL_LABEL[ev.signal] ?? ev.signal}
                      </span>
                    </div>
                    <div className="mt-1 text-sm">{ev.reason}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      Equity {num(ev.equity)} · indicadores {Object.keys(ev.indicators).length}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Panel>
      </div>

      <Panel
        title="Biblioteca de Estratégias"
        subtitle="Ativas, arquivadas, experimentais e histórico de versões."
        action={<BookOpenCheck className="h-4 w-4 text-muted-foreground" />}
      >
        {strategies.isLoading && <LoadingBlock label="Carregando biblioteca..." />}
        {strategies.isError && <InlineError error={strategies.error} title="Falha na biblioteca" />}
        {strategies.data && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(["active", "experimental", "archived"] as QuantLabStrategyStatus[]).map((status) => (
              <div key={status} className="space-y-3">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <Tags className="h-4 w-4 text-muted-foreground" />
                  {status === "active"
                    ? "Ativas"
                    : status === "archived"
                      ? "Arquivadas"
                      : "Experimentais"}
                </div>
                {strategies.data.items
                  .filter((item) => item.status === status)
                  .map((item) => (
                    <div
                      key={item.id}
                      className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
                    >
                      <div className="font-medium">{item.id}</div>
                      <div className="text-xs text-muted-foreground">{item.label}</div>
                      <div className="mt-3 grid grid-cols-2 gap-3">
                        <MetricRow label="Experimentos" value={String(item.experiment_count)} />
                        <MetricRow label="Versões" value={item.versions.join(", ")} />
                      </div>
                      <select
                        value={item.status}
                        onChange={(e) =>
                          updateStrategy.mutate({
                            strategyId: item.id,
                            status: e.target.value as QuantLabStrategyStatus,
                            note: item.note,
                          })
                        }
                        className="mt-3 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
                      >
                        {strategies.data.statuses.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    </div>
                  ))}
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
