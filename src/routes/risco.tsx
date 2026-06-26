import { createFileRoute } from "@tanstack/react-router";
import { PageHeader, Panel } from "@/components/ui/page";
import { useRisk, useUpdateRisk } from "@/lib/queries";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/risco")({
  head: () => ({ meta: [{ title: "Gestão de Risco · Quantum-Trend" }] }),
  component: Page,
});

type RiskField =
  | "risk_per_trade_pct"
  | "daily_stop_pct"
  | "daily_target_pct"
  | "max_ops_per_day"
  | "pause_after_losses"
  | "cooldown_minutes";

const RISK_GUIDES: {
  field: RiskField;
  label: string;
  min: number;
  max: number;
  step: number;
  suffix: string;
  summary: string;
  guide: string;
  tip: string;
}[] = [
  {
    field: "risk_per_trade_pct",
    label: "Risco por operação",
    min: 0.1,
    max: 5,
    step: 0.1,
    suffix: "%",
    summary: "Quanto do saldo você arrisca em cada trade.",
    guide:
      "Define o tamanho da posição com base no stop da estratégia. Ex.: 1% em conta de $10.000 ≈ $100 de risco máximo se o stop for atingido. Valores baixos (0,5–1%) protegem em sequências de perdas; valores altos (2–3%) aceleram ganhos, mas amplificam drawdowns.",
    tip: "Paper/demo: comece entre 0,5% e 1%. Só suba após várias semanas estáveis.",
  },
  {
    field: "daily_stop_pct",
    label: "Stop diário",
    min: 1,
    max: 10,
    step: 0.5,
    suffix: "%",
    summary: "Limite de perda acumulada no dia — ao bater, o bot para.",
    guide:
      "Protege contra dias ruins ou bugs de mercado. Se o P&L do dia cair abaixo desse percentual do saldo, novas entradas são bloqueadas até o dia seguinte. Um stop de 3% em $10.000 = -$300 no dia.",
    tip: "Regra prática: 2–3× o risco por trade. Com 1% por trade, use stop diário entre 2% e 3%.",
  },
  {
    field: "daily_target_pct",
    label: "Meta diária",
    min: 1,
    max: 20,
    step: 0.5,
    suffix: "%",
    summary: "Objetivo de lucro no dia — opcional, para disciplina.",
    guide:
      "Quando o lucro do dia atinge esse percentual, o bot pode pausar novas entradas (preservar ganhos). Não é garantia de performance — serve para evitar overtrading após um bom dia.",
    tip: "Meta realista em tendência: 1,5× a 3× o risco por trade. Evite metas acima de 5% no paper.",
  },
  {
    field: "max_ops_per_day",
    label: "Máximo de operações / dia",
    min: 1,
    max: 100,
    step: 1,
    suffix: "",
    summary: "Teto de trades abertos + fechados no mesmo dia.",
    guide:
      "Evita excesso de entradas em mercados laterais ou quando várias estratégias disparam juntas. Cada slot paper conta como operação independente — com até 12 slots (6 BTC + 6 ETH), use um teto que faça sentido para sua rotina (ex.: 15–30).",
    tip: "Menos operações costuma melhorar qualidade. Se o bot estoura o limite cedo, revise regime ou número de slots.",
  },
  {
    field: "pause_after_losses",
    label: "Pausar após N perdas consecutivas",
    min: 1,
    max: 10,
    step: 1,
    suffix: "",
    summary: "Pausa automática após uma sequência de trades perdedores.",
    guide:
      "Interrompe o bot quando há N perdas seguidas — sinal de que o mercado mudou ou a estratégia não está alinhada ao regime. Força uma pausa para reavaliar antes de continuar.",
    tip: "3 perdas seguidas é um bom padrão inicial. Em alta volatilidade, use 2; em swing 4H/1D, 3–4.",
  },
  {
    field: "cooldown_minutes",
    label: "Cooldown automático",
    min: 5,
    max: 180,
    step: 5,
    suffix: " min",
    summary: "Tempo de espera após pausa por perdas antes de retomar.",
    guide:
      "Depois que o limite de perdas consecutivas dispara, o bot aguarda esse intervalo antes de permitir novas entradas. Evita reentrada impulsiva no mesmo movimento adverso.",
    tip: "30 min funciona bem em 1H; em 4H/1D, 60–120 min pode ser mais coerente com o timeframe.",
  },
];

function RiskSlider({
  label,
  value,
  min,
  max,
  step,
  suffix,
  summary,
  guide,
  tip,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix: string;
  summary: string;
  guide: string;
  tip: string;
  onChange: (v: number) => void;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4 space-y-3">
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium">{label}</label>
          <span className="num text-sm text-gradient-primary">
            {value}
            {suffix}
          </span>
        </div>
        <p className="text-xs text-muted-foreground mb-3">{summary}</p>
        <div className="relative h-2 rounded-full bg-white/5">
          <div
            className="absolute h-full rounded-full bg-gradient-to-r from-[#7C3AED] to-[#3B82F6]"
            style={{ width: `${pct}%` }}
          />
          <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            className="absolute inset-0 w-full opacity-0 cursor-pointer"
          />
          <div
            className="absolute -top-1.5 h-5 w-5 rounded-full bg-white border-2 border-[#7C3AED] shadow-lg"
            style={{ left: `calc(${pct}% - 10px)` }}
          />
        </div>
      </div>
      <div className="text-xs text-muted-foreground leading-relaxed border-t border-white/5 pt-3 space-y-2">
        <p>{guide}</p>
        <p className="text-secondary/90">
          <span className="font-medium text-secondary">Sugestão:</span> {tip}
        </p>
      </div>
    </div>
  );
}

function Page() {
  const { data, isPending, error, isError, isFetching } = useRisk();
  const update = useUpdateRisk();
  const [local, setLocal] = useState({
    risk_per_trade_pct: 1,
    daily_stop_pct: 3,
    daily_target_pct: 5,
    max_ops_per_day: 20,
    pause_after_losses: 3,
    cooldown_minutes: 30,
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

  if (isPending && !data) return <div className="text-muted-foreground text-sm">Carregando risco…</div>;
  if ((isError && !data) || !data) return <div className="text-destructive text-sm">Erro ao carregar gestão de risco.</div>;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Gestão de Risco"
        subtitle="Limites do bot paper — sincronizados com o engine Atlas. Ajuste cada controle com calma: eles definem quanto você arrisca, quando parar e como se proteger."
      />
      {isFetching && (
        <p className="text-xs text-muted-foreground">Atualizando saldo demo…</p>
      )}

      <Panel title="Como usar esta página">
        <div className="text-sm text-muted-foreground space-y-2 leading-relaxed">
          <p>
            Os sliders abaixo controlam o <strong className="text-white">RiskManager</strong> em tempo real. Cada alteração
            é salva automaticamente e vale para todos os slots paper (BTC e ETH) enquanto o bot estiver parado ou rodando.
          </p>
          <p>
            O <strong className="text-white">resumo à direita</strong> traduz os percentuais em valores em dólares com base
            no saldo demo atual. Use-o para sentir o impacto prático antes de subir o risco.
          </p>
        </div>
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Panel title="Parâmetros" className="lg:col-span-2">
          <div className="space-y-4">
            {RISK_GUIDES.map((g) => (
              <RiskSlider
                key={g.field}
                label={g.label}
                value={local[g.field]}
                min={g.min}
                max={g.max}
                step={g.step}
                suffix={g.suffix}
                summary={g.summary}
                guide={g.guide}
                tip={g.tip}
                onChange={(v) => save({ [g.field]: v })}
              />
            ))}
          </div>
        </Panel>

        <div className="space-y-6">
          <Panel title="Resumo de Risco">
            <p className="text-xs text-muted-foreground mb-3">
              Valores estimados com saldo demo de ${data.balance.toLocaleString()} — recalculados ao mover os sliders.
            </p>
            <ul className="space-y-3 text-sm">
              <li className="flex justify-between">
                <span className="text-muted-foreground">Exposição máxima</span>
                <span className="num">${data.summary.max_exposure.toLocaleString()}</span>
              </li>
              <li className="flex justify-between">
                <span className="text-muted-foreground">Perda máxima diária</span>
                <span className="num text-destructive">-${data.summary.max_daily_loss.toLocaleString()}</span>
              </li>
              <li className="flex justify-between">
                <span className="text-muted-foreground">Meta diária</span>
                <span className="num text-success">+${data.summary.daily_target.toLocaleString()}</span>
              </li>
              <li className="flex justify-between">
                <span className="text-muted-foreground">P&L hoje</span>
                <span className="num">${data.settings.daily_pnl.toFixed(2)}</span>
              </li>
            </ul>
          </Panel>
          <Panel title="Proteções Ativas">
            <ul className="space-y-2 text-sm">
              {data.protections.map((p) => (
                <li key={p} className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-success" />
                  {p}
                </li>
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
