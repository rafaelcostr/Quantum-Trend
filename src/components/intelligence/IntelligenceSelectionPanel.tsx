import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { Panel } from "@/components/ui/page";
import { useSettings, useUpdateOperationalSlots } from "@/lib/queries";
import type {
  IntelligenceAssetSelection,
  IntelligencePack,
  IntelligencePick,
  IntelligenceRankedStrategy,
  OperatedBase,
  PaperSlotConfig,
} from "@/lib/api";
import {
  ArrowRight,
  CheckCircle2,
  Loader2,
  Sparkles,
  TrendingDown,
  TrendingUp,
  ArrowLeftRight,
} from "lucide-react";

type PackId = "bull_range" | "bear_range";

const MARKET_META = {
  bull: {
    label: "Alta",
    icon: TrendingUp,
    chip: "text-success border-success/30 bg-success/10",
  },
  bear: {
    label: "Baixa",
    icon: TrendingDown,
    chip: "text-destructive border-destructive/30 bg-destructive/10",
  },
  range: {
    label: "Lateral",
    icon: ArrowLeftRight,
    chip: "text-sky-300 border-sky-500/30 bg-sky-500/10",
  },
} as const;

function scoreColor(n: number) {
  if (n >= 80) return "#22C55E";
  if (n >= 65) return "#7C3AED";
  if (n >= 50) return "#F59E0B";
  return "#EF4444";
}

function mergeSlotsForBase(
  current: PaperSlotConfig[] | undefined,
  base: OperatedBase,
  packSlots: IntelligencePick[],
  marketDefault: PaperSlotConfig,
): PaperSlotConfig[] {
  const rows = current ?? [];
  let normalized: PaperSlotConfig[];
  if (rows.length >= 12) {
    normalized = rows.slice(0, 12).map((slot, globalIdx) => ({
      ...marketDefault,
      ...slot,
      base: (globalIdx < 6 ? "BTC" : "ETH") as OperatedBase,
      quote: slot.quote ?? "USDT",
    }));
  } else {
    const byBase: Record<OperatedBase, PaperSlotConfig[]> = { BTC: [], ETH: [] };
    for (const slot of rows) {
      const b = (slot.base ?? "BTC") as OperatedBase;
      if (byBase[b].length < 6) byBase[b].push({ ...slot, base: b });
    }
    for (const b of ["BTC", "ETH"] as const) {
      while (byBase[b].length < 6) {
        byBase[b].push({ ...marketDefault, base: b, enabled: false });
      }
    }
    normalized = [...byBase.BTC.slice(0, 6), ...byBase.ETH.slice(0, 6)];
  }

  const incoming: PaperSlotConfig[] = packSlots.map((s) => ({
    strategy: s.strategy,
    timeframe: s.timeframe,
    quote: s.quote ?? "USDT",
    base,
    enabled: s.enabled,
  }));

  const offset = base === "BTC" ? 0 : 6;
  const out = [...normalized];
  for (let i = 0; i < 6; i++) {
    out[offset + i] = incoming[i] ?? { ...marketDefault, base, enabled: false };
  }
  return out.slice(0, 12);
}

function RankRow({ row }: { row: IntelligenceRankedStrategy }) {
  const meta = MARKET_META[row.market_type];
  const Icon = meta.icon;
  return (
    <div className="flex items-center gap-3 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2.5">
      <span className="num text-xs w-6 text-muted-foreground">#{row.rank}</span>
      <Icon className="h-3.5 w-3.5 shrink-0 opacity-70" />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{row.name}</div>
        <div className="text-[11px] text-muted-foreground">
          {row.timeframe.toUpperCase()} · PF {row.pf.toFixed(2)} · WR {row.winrate.toFixed(1)}%
        </div>
      </div>
      {row.atlas_score != null && (
        <span className="num text-xs" style={{ color: scoreColor(row.atlas_score) }}>
          {row.atlas_score}
        </span>
      )}
    </div>
  );
}

function SlotCard({ slot, index }: { slot: IntelligencePick; index: number }) {
  const meta = MARKET_META[slot.market_type];
  const Icon = meta.icon;
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[11px] text-muted-foreground">Slot {index + 1}</div>
          <div className="text-sm font-medium truncate">{slot.name}</div>
        </div>
        <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] ${meta.chip}`}>
          <Icon className="h-3 w-3" />
          {meta.label}
        </span>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
        <span>{slot.timeframe.toUpperCase()}</span>
        {slot.atlas_score != null && <span className="num">Score {slot.atlas_score}</span>}
        {slot.pf != null && <span className="num">PF {slot.pf}</span>}
        {slot.source === "default" && <span className="text-warning">Sugerido</span>}
      </div>
    </div>
  );
}

function AssetPanel({
  asset,
  packChoice,
  onPackChoice,
}: {
  asset: IntelligenceAssetSelection;
  packChoice: PackId;
  onPackChoice: (id: PackId) => void;
}) {
  const settings = useSettings();
  const saveSlots = useUpdateOperationalSlots();
  const [msg, setMsg] = useState<string | null>(null);
  const pack: IntelligencePack = asset.packs[packChoice];
  const botRunning = settings.data?.system.bot_running;

  const apply = () => {
    setMsg(null);
    const merged = mergeSlotsForBase(
      settings.data?.operational?.slots,
      asset.base,
      pack.slots,
      {
        strategy: pack.slots[0]?.strategy ?? "pullback_ema20_v1",
        timeframe: "4h",
        quote: "USDT",
        base: asset.base,
        enabled: false,
      },
    );
    saveSlots.mutate(merged, {
      onSuccess: () =>
        setMsg(`${pack.label} aplicado em ${asset.base} — 6 slots prontos. Inicie o paper no Dashboard.`),
      onError: (e) => setMsg(e instanceof Error ? e.message : "Erro ao aplicar slots"),
    });
  };

  return (
    <Panel
      title={`${asset.base}/USDT`}
      subtitle={`${asset.total_backtests} backtests · Atlas Score ${asset.atlas_score}`}
    >
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-2">
          {(["bull_range", "bear_range"] as const).map((id) => {
            const p = asset.packs[id];
            const active = packChoice === id;
            const TrendIcon = id === "bull_range" ? TrendingUp : TrendingDown;
            return (
              <button
                key={id}
                type="button"
                onClick={() => onPackChoice(id)}
                className={`rounded-xl border p-3 text-left transition ${
                  active
                    ? "border-primary/50 bg-primary/10 ring-1 ring-primary/30"
                    : "border-white/10 bg-white/[0.02] hover:bg-white/[0.04]"
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <TrendIcon className={`h-4 w-4 ${id === "bull_range" ? "text-success" : "text-destructive"}`} />
                  <ArrowLeftRight className="h-3.5 w-3.5 text-sky-300" />
                  <span className="text-sm font-medium">{p.label}</span>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed">{p.description}</p>
                <p className="text-[10px] text-muted-foreground mt-2">
                  {p.backtest_count}/6 com backtest salvo
                </p>
              </button>
            );
          })}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {pack.slots.map((slot, i) => (
            <SlotCard key={`${slot.strategy}-${slot.timeframe}-${i}`} slot={slot} index={i} />
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={saveSlots.isPending || botRunning}
            onClick={apply}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#7C3AED] to-[#3B82F6] px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {saveSlots.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <CheckCircle2 className="h-4 w-4" />
            )}
            Aplicar 6 slots · {asset.base}
          </button>
          <Link
            to={pack.route}
            className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
          >
            Ajustar manualmente
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {botRunning && (
          <p className="text-xs text-warning">Pare o bot antes de alterar slots.</p>
        )}
        {msg && <p className="text-xs text-success">{msg}</p>}
      </div>
    </Panel>
  );
}

export function IntelligenceSelectionPanel({
  selection,
}: {
  selection: NonNullable<import("@/lib/api").IntelligenceSelectionPayload>;
}) {
  const [packByBase, setPackByBase] = useState<Record<OperatedBase, PackId>>({
    BTC: "bull_range",
    ETH: "bull_range",
  });

  return (
    <div className="space-y-6">
      <Panel className="border-secondary/20 bg-secondary/5">
        <div className="flex gap-3">
          <Sparkles className="h-5 w-5 text-secondary shrink-0 mt-0.5" />
          <div className="text-sm space-y-2 text-muted-foreground">
            <p className="text-foreground font-medium">Seleção rápida — 6 slots por moeda</p>
            <p>
              Escolha <strong className="text-foreground">Alta + Lateral</strong> ou{" "}
              <strong className="text-foreground">Baixa + Lateral</strong> para BTC e ETH. A IA monta 3 estratégias de
              tendência + 3 laterais com base nos melhores backtests salvos. Um clique aplica os 6 slots no paper.
            </p>
          </div>
        </div>
      </Panel>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {selection.assets.map((asset) => (
          <AssetPanel
            key={asset.base}
            asset={asset}
            packChoice={packByBase[asset.base]}
            onPackChoice={(id) => setPackByBase((prev) => ({ ...prev, [asset.base]: id }))}
          />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {(["bull", "bear", "range"] as const).map((market) => {
          const meta = MARKET_META[market];
          const Icon = meta.icon;
          return (
            <Panel
              key={market}
              title={`Top 6 · ${meta.label}`}
              action={
                <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] ${meta.chip}`}>
                  <Icon className="h-3 w-3" />
                  {meta.label}
                </span>
              }
            >
              <div className="space-y-4">
                {selection.assets.map((asset) => (
                  <div key={asset.base}>
                    <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">{asset.base}</div>
                    {asset.groups[market].length === 0 ? (
                      <p className="text-xs text-muted-foreground">Sem backtests — rode a matriz em Backtests.</p>
                    ) : (
                      <div className="space-y-2">
                        {asset.groups[market].map((row) => (
                          <RankRow key={`${asset.base}-${row.strategy}-${row.timeframe}`} row={row} />
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
