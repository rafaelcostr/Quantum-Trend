import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { PageHeader, Panel } from "@/components/ui/page";
import { IntelligenceSelectionPanel } from "@/components/intelligence/IntelligenceSelectionPanel";
import { useIntelligence, useIntelligenceAnalysis } from "@/lib/queries";
import type { EducationalMetric, Level1Snapshot, MetricReading, Strategy } from "@/lib/api";
import {
  Bot,
  Sparkles,
  Trophy,
  Brain,
  FlaskConical,
  Microscope,
  Loader2,
  Info,
} from "lucide-react";

export const Route = createFileRoute("/ia")({
  head: () => ({ meta: [{ title: "IA de Seleção · Quantum-Trend" }] }),
  component: Page,
});

const TABS = [
  { id: "l1", label: "Nível 1 — Decisão", icon: Brain },
  { id: "l2", label: "Nível 2 — Diagnóstico", icon: FlaskConical },
  { id: "l3", label: "Nível 3 — Research", icon: Microscope },
] as const;

const RANK_TABS = [
  { id: "all", label: "Todas" },
  { id: "bull", label: "Alta" },
  { id: "bear", label: "Baixa" },
  { id: "range", label: "Lateral" },
] as const;

function scoreColor(n: number) {
  if (n >= 80) return "#22C55E";
  if (n >= 65) return "#7C3AED";
  if (n >= 50) return "#F59E0B";
  return "#EF4444";
}

function inferMarketType(s: Strategy): "bull" | "bear" | "range" {
  const mt = s.market_type ?? s.strategy_category;
  if (mt === "bear" || mt === "bull" || mt === "range") return mt;
  const id = (s.id || s.name || "").toLowerCase();
  if (id.includes("short") || id.includes("_bear") || id.includes("breakout_down")) return "bear";
  if (id.startsWith("range_") || id.includes("bb_squeeze") || id.includes("regime_switching"))
    return "range";
  return "bull";
}

function MetricTable({ metrics }: { metrics: MetricReading[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <tbody>
          {metrics.map((m) => (
            <tr key={m.key} className="border-b border-white/5">
              <td className="py-2 pr-4 text-muted-foreground">{m.label}</td>
              <td className="py-2 num">
                {m.emoji} {m.display}
              </td>
              <td className="py-2 text-right text-xs text-muted-foreground">{m.status_text}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BulletList({ items, tone }: { items: string[]; tone: "success" | "warning" | "danger" }) {
  const colors = { success: "text-success", warning: "text-warning", danger: "text-destructive" };
  return (
    <ul className={`space-y-1 text-sm ${colors[tone]}`}>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function EducationalCards({ metrics }: { metrics: EducationalMetric[] }) {
  if (!metrics.length) {
    return (
      <p className="text-sm text-muted-foreground">Sem métricas disponíveis para este nível.</p>
    );
  }
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {metrics.map((edu) => (
        <div
          key={edu.reading.key}
          className="rounded-xl border border-white/5 bg-white/[0.02] p-4 space-y-2"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium">{edu.reading.label}</span>
            <span className="num text-sm">
              {edu.reading.emoji} {edu.reading.display}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">{edu.what_is}</p>
          <p className="text-xs">{edu.why_matters}</p>
          <p className="text-[11px] text-secondary">{edu.bands_text}</p>
        </div>
      ))}
    </div>
  );
}

function Level1Panel({ l1 }: { l1: Level1Snapshot }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <div className="text-xs uppercase text-muted-foreground mb-1">Atlas Score</div>
          <div className="num text-4xl text-gradient-primary">{l1.atlas_score}</div>
          <div className="text-sm mt-1">
            {l1.score_emoji} {l1.score_label}
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <div className="text-xs uppercase text-muted-foreground mb-1">Confiança</div>
          <div className="text-lg">
            {l1.confidence_emoji} {l1.confidence}
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <div className="text-xs uppercase text-muted-foreground mb-1">Overfitting (L1)</div>
          <div className="text-lg">
            {l1.overfitting_emoji} {l1.overfitting_risk}
          </div>
        </div>
      </div>

      <Panel title="Métricas principais">
        <MetricTable metrics={l1.metrics} />
      </Panel>

      <p className="text-sm text-muted-foreground leading-relaxed">{l1.summary}</p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Panel title="Pontos fortes">
          <BulletList items={l1.strengths} tone="success" />
        </Panel>
        <Panel title="Pontos fracos">
          <BulletList items={l1.weaknesses} tone="warning" />
        </Panel>
        <Panel title="Riscos">
          <BulletList items={l1.risks} tone="danger" />
        </Panel>
      </div>

      <Panel title="Checklist Backtest → Paper">
        <ul className="space-y-2">
          {l1.promotion_backtest_paper.map((c) => (
            <li
              key={c.label}
              className="flex items-center gap-3 text-sm rounded-lg bg-white/[0.02] px-3 py-2"
            >
              <span className={c.ok ? "text-success" : "text-destructive"}>{c.ok ? "✓" : "✗"}</span>
              <span className="flex-1">{c.label}</span>
              <span className="text-xs text-muted-foreground num">{c.value}</span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}

function Page() {
  const { data, isPending, error, isError } = useIntelligence();
  const analysisQuery = useIntelligenceAnalysis(!isPending && !!data);
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("l1");
  const [rankTab, setRankTab] = useState<(typeof RANK_TABS)[number]["id"]>("all");

  if (isPending && !data) {
    return <div className="text-muted-foreground text-sm">Carregando ranking de estratégias…</div>;
  }
  if (isError && !data) {
    const msg = error instanceof Error ? error.message : "Erro desconhecido";
    return (
      <div className="text-destructive text-sm space-y-2">
        <p>
          Erro ao carregar IA de seleção. Confirme que a API Python está ativa (
          <code className="text-secondary">python -m atlas.cli api</code>).
        </p>
        <p className="text-xs text-muted-foreground">{msg.slice(0, 240)}</p>
      </div>
    );
  }
  if (!data) return null;

  const strategies = [...data.strategies].sort((a, b) => b.pf - a.pf);
  const filteredStrategies =
    rankTab === "all" ? strategies : strategies.filter((s) => inferMarketType(s) === rankTab);
  const analysis = analysisQuery.data;
  const l1 = analysis?.level1;
  const l2 = analysis?.level2;
  const l3 = analysis?.level3;

  return (
    <div className="space-y-8">
      <PageHeader
        title="IA de Seleção"
        subtitle="Compare backtests por regime, aplique 6 slots por moeda (Alta+Lateral ou Baixa+Lateral) e leia a análise Atlas L1/L2/L3."
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Panel className="relative overflow-hidden">
          <div className="absolute -top-20 -right-20 h-40 w-40 rounded-full blur-3xl opacity-40 bg-primary" />
          <div className="flex items-center gap-3 mb-3">
            <Bot className="h-5 w-5 text-primary" />
            <span className="text-xs uppercase tracking-wider text-muted-foreground">
              Estratégias Avaliadas
            </span>
          </div>
          <div className="num text-4xl">{data.strategies_evaluated}</div>
        </Panel>
        <Panel className="relative overflow-hidden">
          <div className="absolute -top-20 -right-20 h-40 w-40 rounded-full blur-3xl opacity-40 bg-success" />
          <div className="flex items-center gap-3 mb-3">
            <Trophy className="h-5 w-5 text-success" />
            <span className="text-xs uppercase tracking-wider text-muted-foreground">
              Melhor Estratégia
            </span>
          </div>
          <div className="num text-2xl">{data.best_strategy}</div>
          <div className="text-xs text-success mt-1">Score {data.best_score}</div>
        </Panel>
        <Panel className="relative overflow-hidden">
          <div className="absolute -top-20 -right-20 h-40 w-40 rounded-full blur-3xl opacity-40 bg-secondary" />
          <div className="flex items-center gap-3 mb-3">
            <Sparkles className="h-5 w-5 text-secondary" />
            <span className="text-xs uppercase tracking-wider text-muted-foreground">
              Atlas Score
            </span>
          </div>
          <div className="num text-4xl text-gradient-primary">
            {l1?.atlas_score ?? data.overall_score}
          </div>
          {analysis && (
            <div className="text-xs text-muted-foreground mt-1">
              {analysis.strategy} · {analysis.market} · {analysis.timeframe}
            </div>
          )}
        </Panel>
      </div>

      {data.selection && <IntelligenceSelectionPanel selection={data.selection} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Ranking por Regime">
          <div className="flex flex-wrap gap-2 mb-4">
            {RANK_TABS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                onClick={() => setRankTab(id)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  rankTab === id
                    ? "bg-primary/20 text-primary border border-primary/30"
                    : "bg-white/5 text-muted-foreground border border-white/10 hover:bg-white/10"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          {filteredStrategies.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nenhum backtest salvo. Rode testes em{" "}
              <Link to="/backtests" className="text-primary hover:underline">
                Backtests
              </Link>
              .
            </p>
          ) : (
            <ol className="space-y-2">
              {filteredStrategies.map((s, i) => {
                const mt = inferMarketType(s);
                const badge =
                  mt === "bear"
                    ? "text-destructive"
                    : mt === "range"
                      ? "text-sky-300"
                      : "text-success";
                return (
                  <li
                    key={s.id || s.name}
                    className="flex items-center gap-3 rounded-xl bg-white/[0.03] border border-white/5 px-4 py-3"
                  >
                    <span
                      className={`num text-sm w-6 ${i < 3 ? "text-gradient-primary" : "text-muted-foreground"}`}
                    >
                      #{i + 1}
                    </span>
                    <div className="flex-1">
                      <div className="text-sm font-medium">{s.name}</div>
                      <div className="text-[11px] text-muted-foreground">
                        <span className={badge}>
                          {mt === "bull" ? "Alta" : mt === "bear" ? "Baixa" : "Lateral"}
                        </span>
                        {" · "}
                        PF {s.pf} · WR {s.winrate}% · DD {s.dd}%
                      </div>
                    </div>
                    <div
                      className="num text-sm"
                      style={{ color: scoreColor(s.winrate + s.pf * 10) }}
                    >
                      {Math.round(s.winrate + s.pf * 10)}
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </Panel>

        <Panel title="Mapa de Oportunidades (Atlas Score)">
          <div className="grid grid-cols-2 gap-3">
            {data.heatmap.map((a) => {
              const c = scoreColor(a.score);
              return (
                <div
                  key={a.sym}
                  className="aspect-square rounded-xl border flex flex-col items-center justify-center transition hover:scale-[1.04]"
                  style={{
                    background: `linear-gradient(135deg, ${c}33, ${c}11)`,
                    borderColor: `${c}44`,
                    boxShadow: `0 0 30px -10px ${c}66`,
                  }}
                >
                  <div className="text-sm font-semibold">{a.sym}/USDT</div>
                  <div className="num text-2xl mt-1" style={{ color: c }}>
                    {a.score}
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      </div>

      <Panel title="Atlas Intelligence — Análise profunda">
        <Panel className="border-primary/20 bg-primary/5 mb-6">
          <div className="flex gap-3">
            <Info className="h-5 w-5 text-primary shrink-0 mt-0.5" />
            <div className="text-sm space-y-1 text-muted-foreground">
              <p>
                A <strong className="text-foreground">seleção rápida</strong> acima usa a matriz de
                backtests. A análise abaixo aprofunda o relatório ativo (L1 decisão, L2 diagnóstico,
                L3 research/overfitting).
              </p>
            </div>
          </div>
        </Panel>

        {analysisQuery.isPending && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-6">
            <Loader2 className="h-4 w-4 animate-spin" />
            Calculando análise L1/L2/L3 do backtest ativo…
          </div>
        )}
        {analysisQuery.isError && (
          <p className="text-sm text-warning">
            Não foi possível carregar a análise profunda. O ranking e a seleção rápida continuam
            válidos.
          </p>
        )}
        {!analysisQuery.isPending && !l1 && (
          <p className="text-sm text-warning">
            Rode um backtest primeiro (
            <code className="text-secondary">python -m atlas.cli backtest</code> ou página{" "}
            <Link to="/backtests" className="text-primary hover:underline">
              Backtests
            </Link>
            ) para gerar relatório em data/reports/.
          </p>
        )}
        {l1 && (
          <>
            <div className="flex flex-wrap gap-2 mb-6">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setTab(id)}
                  className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-medium transition ${
                    tab === id
                      ? "bg-gradient-to-r from-[#7C3AED] to-[#3B82F6] text-white"
                      : "bg-white/5 border border-white/10 text-muted-foreground hover:bg-white/10"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </button>
              ))}
            </div>

            {tab === "l1" && <Level1Panel l1={l1} />}

            {tab === "l2" && l2 && (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground leading-relaxed">{l2.diagnosis}</p>
                <EducationalCards metrics={l2.metrics} />
              </div>
            )}

            {tab === "l3" && l3 && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-sm">
                  <span>{l3.overfitting_emoji}</span>
                  <span className="font-medium">Risco OOS:</span>
                  <span className="text-muted-foreground">{l3.overfitting_risk}</span>
                  {!l3.has_walkforward && (
                    <span className="text-xs text-warning ml-2">· Walk-forward pendente</span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">{l3.diagnosis}</p>
                <EducationalCards metrics={l3.metrics} />
              </div>
            )}
          </>
        )}
      </Panel>
    </div>
  );
}
