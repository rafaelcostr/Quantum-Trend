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
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium">{ev.title}</span>
                        <span className="text-[10px] num text-muted-foreground shrink-0">{ev.timeLabel}</span>
                      </div>
                      {ev.subtitle && <p className="text-xs text-muted-foreground mt-0.5">{ev.subtitle}</p>}
                      {ev.detail && ev.detail.length > 0 && (
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
