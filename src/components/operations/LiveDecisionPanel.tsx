import { Brain } from "lucide-react";
import { Panel } from "@/components/ui/page";
import type { DecisionView } from "@/lib/operations-terminal";
import { ConfidenceBar } from "./ConfidenceBar";

export function LiveDecisionPanel({ decision }: { decision: DecisionView }) {
  return (
    <Panel title="Decisão da IA" subtitle="Síntese do runtime · por que entrou ou aguardou">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-3 text-sm">
          <Row label="Mercado" value={decision.regime} />
          <Row label="Alignment" value={`${Math.round(decision.alignmentScore)}/100`} />
          <Row label="Probabilidade de entrada" value={`${Math.round(decision.entryProbability)}%`} highlight />
          <Row label="Ação" value={decision.action} />
          {decision.strategyLabel && <Row label="Engine foco" value={decision.strategyLabel} />}
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-2">Confiança do setup</div>
          <ConfidenceBar value={decision.entryProbability} />
          <div className="mt-4 text-[10px] uppercase tracking-wide text-muted-foreground mb-2">Motivos</div>
          <ul className="space-y-1.5 text-xs">
            {decision.motives.map((m, i) => (
              <li key={i} className={m.ok ? "text-success" : "text-muted-foreground"}>
                {m.ok ? "✅" : "❌"} {m.text}
              </li>
            ))}
          </ul>
          {decision.timeframes.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {decision.timeframes.map((tf) => (
                <span
                  key={tf.tf}
                  className={`text-[10px] rounded-md px-2 py-1 border ${
                    tf.ok ? "border-success/30 bg-success/10 text-success" : "border-white/10 bg-white/[0.03]"
                  }`}
                >
                  {tf.tf} {tf.ok ? "✅" : "❌"} {tf.label}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="mt-4 flex items-start gap-2 rounded-xl border border-primary/20 bg-primary/5 px-3 py-2 text-xs text-muted-foreground">
        <Brain className="h-4 w-4 text-primary shrink-0 mt-0.5" />
        <span>{decision.summary}</span>
      </div>
    </Panel>
  );
}

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex justify-between gap-3 border-b border-white/5 pb-2">
      <span className="text-muted-foreground">{label}</span>
      <span className={`font-medium num text-right ${highlight ? "text-primary" : ""}`}>{value}</span>
    </div>
  );
}
