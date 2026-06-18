import { motion, AnimatePresence } from "framer-motion";
import {
  AlertCircle,
  ArrowDownCircle,
  ArrowUpCircle,
  Ban,
  CircleDot,
  RefreshCw,
  Radio,
} from "lucide-react";
import { Panel } from "@/components/ui/page";
import type { TimelineEventView } from "@/lib/operations-terminal";
import { ConfidenceBar } from "./ConfidenceBar";

const ICONS = {
  signal: Radio,
  entry: ArrowUpCircle,
  exit: ArrowDownCircle,
  error: AlertCircle,
  sync: RefreshCw,
  hold: CircleDot,
  blocked: Ban,
} as const;

const TONE_BORDER = {
  success: "border-success/30 bg-success/5",
  danger: "border-destructive/30 bg-destructive/5",
  warning: "border-warning/30 bg-warning/5",
  info: "border-primary/30 bg-primary/5",
  neutral: "border-white/10 bg-white/[0.02]",
} as const;

const DECISION_CLS: Record<string, string> = {
  ENTER: "text-success",
  HOLD: "text-muted-foreground",
  EXIT: "text-destructive",
  BLOCKED: "text-warning",
  SIGNAL: "text-primary",
};

export function RuntimeTimeline({ events }: { events: TimelineEventView[] }) {
  return (
    <Panel title="Timeline do runtime" subtitle="Eventos cronológicos · ticks · execuções · decisões">
      <ul className="space-y-2 max-h-[28rem] overflow-y-auto pr-1">
        <AnimatePresence initial={false}>
          {events.length === 0 ? (
            <li className="text-sm text-muted-foreground text-center py-8">Aguardando eventos do runtime…</li>
          ) : (
            events.map((ev) => {
              const Icon = ICONS[ev.icon];
              return (
                <motion.li
                  key={ev.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`rounded-xl border px-3 py-2.5 ${TONE_BORDER[ev.tone]}`}
                >
                  <div className="flex gap-3">
                    <div className="shrink-0 mt-0.5">
                      <Icon className="h-4 w-4 opacity-80" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="text-[10px] num text-muted-foreground">{ev.timeLabel}</div>
                          {ev.symbol && (
                            <div className="text-xs font-semibold mt-0.5">{ev.symbol}</div>
                          )}
                          {ev.strategyLabel && (
                            <div className="text-[11px] text-primary">{ev.strategyLabel}</div>
                          )}
                        </div>
                        {ev.score != null && (
                          <span className="text-[10px] num chip shrink-0">{Math.round(ev.score)}/100</span>
                        )}
                      </div>

                      <div className="text-sm font-medium mt-1">{ev.title}</div>

                      {ev.timeframes && ev.timeframes.length > 0 && (
                        <div className="mt-2 space-y-0.5 font-mono text-[11px]">
                          {ev.timeframes.map((tf) => (
                            <div key={tf.tf} className={tf.ok ? "text-success" : "text-muted-foreground"}>
                              {tf.tf} {tf.ok ? "✅" : "❌"} {tf.label}
                            </div>
                          ))}
                        </div>
                      )}

                      {ev.entryProbability != null && (
                        <div className="mt-2 max-w-[140px]">
                          <ConfidenceBar value={ev.entryProbability} />
                        </div>
                      )}

                      {ev.decision && (
                        <div className={`mt-2 text-xs font-medium ${DECISION_CLS[ev.decision] ?? ""}`}>
                          Decisão: {ev.decision}
                        </div>
                      )}

                      {ev.subtitle && !ev.timeframes?.length && (
                        <p className="text-xs text-muted-foreground mt-1">{ev.subtitle}</p>
                      )}

                      {ev.detail && ev.detail.length > 0 && !ev.timeframes?.length && (
                        <ul className="mt-2 space-y-0.5 text-[11px] text-muted-foreground">
                          {ev.detail.map((line, i) => (
                            <li key={i}>{line}</li>
                          ))}
                        </ul>
                      )}

                      <span className="inline-block mt-2 text-[9px] uppercase tracking-wider chip opacity-70">{ev.tag}</span>
                    </div>
                  </div>
                </motion.li>
              );
            })
          )}
        </AnimatePresence>
      </ul>
    </Panel>
  );
}
