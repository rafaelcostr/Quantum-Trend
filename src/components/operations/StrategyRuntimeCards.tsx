import { Area, AreaChart, ResponsiveContainer } from "recharts";
import type { StrategyRuntimeView } from "@/lib/operations-terminal";
import { fmtCountdown, fmtTime } from "@/lib/operations-terminal";
import { ConfidenceBar, ProgressBar } from "./ConfidenceBar";

const STATUS_META = {
  operando: { label: "Operando", dot: "bg-success", text: "text-success" },
  monitorando: { label: "Monitorando", dot: "bg-warning", text: "text-warning" },
  pausado: { label: "Pausado", dot: "bg-destructive", text: "text-destructive" },
} as const;

const SIGNAL_META = {
  compra: { label: "Compra", cls: "text-success border-success/30 bg-success/10" },
  venda: { label: "Venda", cls: "text-destructive border-destructive/30 bg-destructive/10" },
  aguardando: { label: "Aguardando", cls: "text-muted-foreground border-white/10 bg-white/[0.03]" },
} as const;

const CARD_BORDER = {
  success: "border-l-success",
  warning: "border-l-warning",
  danger: "border-l-destructive",
} as const;

const HEALTH_TEXT = {
  healthy: "text-success",
  attention: "text-warning",
  degraded: "text-destructive",
} as const;

function Sparkline({ data }: { data: number[] }) {
  const series = data.length > 1 ? data.map((v, i) => ({ i, v })) : [{ i: 0, v: 50 }, { i: 1, v: 52 }];
  const up = series[series.length - 1]?.v >= series[0]?.v;
  return (
    <div className="h-10 mt-3">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={series}>
          <defs>
            <linearGradient id="sparkOp" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={up ? "#22C55E" : "#EF4444"} stopOpacity={0.45} />
              <stop offset="100%" stopColor={up ? "#22C55E" : "#EF4444"} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="v" stroke={up ? "#22C55E" : "#EF4444"} strokeWidth={1.5} fill="url(#sparkOp)" dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function StrategyCard({ card }: { card: StrategyRuntimeView }) {
  const st = STATUS_META[card.status];
  const sig = SIGNAL_META[card.signal];

  return (
    <div className={`glass rounded-2xl border border-white/10 border-l-4 ${CARD_BORDER[card.cardTone]} p-4 flex flex-col`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">
            {card.statusEmoji} {card.title}
          </h3>
          <p className="text-[11px] text-muted-foreground mt-0.5">{card.subtitle}</p>
        </div>
        <span className={`inline-flex items-center gap-1.5 text-[10px] font-medium ${st.text}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${st.dot}`} />
          {st.label}
        </span>
      </div>

      <div className="mt-3 space-y-1">
        {card.timeframes.map((tf) => (
          <div key={tf.tf} className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-muted-foreground w-8">{tf.tf}</span>
            <span className={tf.ok ? "text-success" : "text-muted-foreground"}>
              {tf.ok ? "✅" : "❌"} {tf.label}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-[11px]">
        <div>
          <div className="text-muted-foreground uppercase tracking-wide">Alignment</div>
          <div className="num text-lg font-semibold mt-0.5">{Math.round(card.alignmentScore)}/100</div>
        </div>
        <div>
          <div className="text-muted-foreground uppercase tracking-wide">Health</div>
          <div className={`num text-lg font-semibold mt-0.5 ${HEALTH_TEXT[card.healthTone]}`}>
            {Math.round(card.healthScore)}/100
          </div>
          <div className={`text-[10px] ${HEALTH_TEXT[card.healthTone]}`}>{card.healthLabel}</div>
        </div>
        <div>
          <div className="text-muted-foreground uppercase tracking-wide">Última análise</div>
          <div className="num mt-0.5">{fmtTime(card.lastAnalysis)}</div>
        </div>
        <div>
          <div className="text-muted-foreground uppercase tracking-wide">Próximo candle</div>
          <div className="num mt-0.5">{fmtCountdown(card.nextCandleSec)}</div>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <div className="text-[10px] text-muted-foreground uppercase mb-1">Confiança</div>
          <ConfidenceBar value={card.confidence} />
        </div>
        <div>
          <ProgressBar value={card.setupProgress} label="Setup Formation" />
        </div>
      </div>

      {card.setupSteps.length > 0 && (
        <div className="mt-2 space-y-0.5">
          {card.setupSteps.map((step) => (
            <div key={step.label} className="flex justify-between text-[10px]">
              <span className="text-muted-foreground">{step.label}</span>
              <span>{step.ok ? "✅" : step.ok === false ? "❌" : "—"}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-3">
        <div className="text-[10px] text-muted-foreground uppercase mb-1">Sinal · {card.regime}</div>
        <span className={`inline-flex rounded-lg border px-2 py-1 text-xs font-medium ${sig.cls}`}>{sig.label}</span>
      </div>

      <div className="mt-auto pt-3 border-t border-white/5">
        <div className="text-[10px] text-muted-foreground uppercase">Decisão</div>
        <p className="text-xs mt-1 leading-relaxed">{card.decision}</p>
      </div>

      <Sparkline data={card.sparkline} />
    </div>
  );
}

export function StrategyRuntimeCards({ cards }: { cards: StrategyRuntimeView[] }) {
  return (
    <div className="flex flex-col gap-3 max-h-[520px] xl:max-h-[560px] overflow-y-auto pr-1">
      <div className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground px-1">
        Estratégias em tempo real
      </div>
      {cards.map((card) => (
        <StrategyCard key={card.key} card={card} />
      ))}
    </div>
  );
}
