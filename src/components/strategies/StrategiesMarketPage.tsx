import { Link } from "@tanstack/react-router";
import { PageHeader, Panel } from "@/components/ui/page";
import { useSettings, useStrategies, useUpdateOperational, useUpdateOperationalSlots } from "@/lib/queries";
import type { PaperSlotConfig, OperationalTimeframe, Strategy } from "@/lib/api";
import { Edit, Copy, Play, MoreHorizontal, Layers } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";

export type StrategyMarket = "bull" | "bear" | "range";

const DEFAULT_STRATEGY: Record<StrategyMarket, string> = {
  bull: "pullback_ema20_v1",
  bear: "pullback_short_v1",
  range: "range_hunter_v1",
};

const PEER_ROUTES: Record<StrategyMarket, { to: string; label: string }[]> = {
  bull: [
    { to: "/estrategias-baixa", label: "Estratégias de Baixa" },
    { to: "/estrategias-lateral", label: "Estratégias Laterais" },
  ],
  bear: [
    { to: "/estrategias-alta", label: "Estratégias de Alta" },
    { to: "/estrategias-lateral", label: "Estratégias Laterais" },
  ],
  range: [
    { to: "/estrategias-alta", label: "Estratégias de Alta" },
    { to: "/estrategias-baixa", label: "Estratégias de Baixa" },
  ],
};

const MARKET_SLOT_LABEL: Record<StrategyMarket, string> = {
  bull: "de alta (Bull)",
  bear: "de baixa (Bear)",
  range: "laterais (Range)",
};

const PAGE_META: Record<
  StrategyMarket,
  { title: string; subtitle: string; tableTitle: string; tableSubtitle: string; badge: ReactNode }
> = {
  bull: {
    title: "Estratégias de Alta",
    subtitle: "Pullback, Breakout e Supertrend Long — ativas em regime de alta (Bull).",
    tableTitle: "Bull Strategies",
    tableSubtitle: "Operações long em tendências de alta.",
    badge: <span className="chip text-success">Bull</span>,
  },
  bear: {
    title: "Estratégias de Baixa",
    subtitle: "Pullback Short, Breakout Down e Supertrend Bear — ativas em mercado de baixa (Bear).",
    tableTitle: "Bear Strategies",
    tableSubtitle: "Operações short em tendências de baixa.",
    badge: <span className="chip text-destructive">Bear</span>,
  },
  range: {
    title: "Estratégias Laterais",
    subtitle: "Range Hunter, BB Squeeze e Regime Switching — ativas em mercado lateral (Range).",
    tableTitle: "Range Strategies",
    tableSubtitle: "Mean reversion e breakout em consolidação.",
    badge: <span className="chip text-warning">Lateral</span>,
  },
};

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

const SLOTS_PER_BASE = 6;
const TOTAL_SLOT_ROWS = SLOTS_PER_BASE * 2;
const DEFAULT_MAX_SLOTS = TOTAL_SLOT_ROWS;

/** Fallback quando /strategies ainda não listou relatórios. */
const STRATEGY_IDS_BY_MARKET: Record<StrategyMarket, string[]> = {
  bull: [
    "quantum_trend_pro",
    "pullback_ema20_v1",
    "breakout_high20_v1",
    "supertrend_mm200_v1",
    "mm200_trend_v1",
    "mm200_trend_v2",
    "mm200_daily_macro_v1",
    "portfolio_macro_micro_v1",
  ],
  bear: ["pullback_short_v1", "breakout_down_v1", "supertrend_bear_v1"],
  range: ["range_hunter_v1", "range_hunter_v2", "bb_squeeze_v1", "regime_switching_v1"],
};

const emptySlot = (market: StrategyMarket, base: "BTC" | "ETH"): PaperSlotConfig => ({
  strategy: DEFAULT_STRATEGY[market],
  timeframe: "4h",
  quote: "USDT",
  base,
  enabled: false,
});

function slotBaseAtIndex(globalIdx: number): "BTC" | "ETH" {
  return globalIdx < SLOTS_PER_BASE ? "BTC" : "ETH";
}

/** Ordem fixa: índices 0–5 BTC, 6–11 ETH (alinha com backend). */
function normalizeSavedSlots(
  saved: PaperSlotConfig[] | undefined,
  market: StrategyMarket,
): PaperSlotConfig[] {
  const rows = saved ?? [];
  if (rows.length >= TOTAL_SLOT_ROWS) {
    return rows.slice(0, TOTAL_SLOT_ROWS).map((slot, globalIdx) => {
      const base = slotBaseAtIndex(globalIdx);
      return {
        ...emptySlot(market, base),
        ...slot,
        base,
        quote: slot.quote ?? "USDT",
      };
    });
  }

  const byBase: Record<"BTC" | "ETH", PaperSlotConfig[]> = { BTC: [], ETH: [] };
  for (const slot of rows) {
    const base = (slot.base ?? "BTC") as "BTC" | "ETH";
    if (byBase[base].length < SLOTS_PER_BASE) {
      byBase[base].push({ ...slot, base });
    }
  }
  for (const base of ["BTC", "ETH"] as const) {
    while (byBase[base].length < SLOTS_PER_BASE) {
      byBase[base].push(emptySlot(market, base));
    }
  }
  return [...byBase.BTC.slice(0, SLOTS_PER_BASE), ...byBase.ETH.slice(0, SLOTS_PER_BASE)];
}

function mergeSlotsForSave(
  pageSlots: PaperSlotConfig[],
  saved: PaperSlotConfig[] | undefined,
  allowedIds: Set<string>,
  market: StrategyMarket,
): PaperSlotConfig[] {
  const prev = normalizeSavedSlots(saved, market);
  const out: PaperSlotConfig[] = [];

  for (let globalIdx = 0; globalIdx < TOTAL_SLOT_ROWS; globalIdx++) {
    const base = slotBaseAtIndex(globalIdx);
    const page = pageSlots[globalIdx] ?? emptySlot(market, base);
    const previous = prev[globalIdx];
    const empty = emptySlot(market, base);
    const touched =
      page.enabled !== (previous?.enabled ?? false) ||
      page.strategy !== (previous?.strategy ?? empty.strategy) ||
      page.timeframe !== (previous?.timeframe ?? empty.timeframe);

    if (touched) {
      if (page.enabled && !allowedIds.has(page.strategy)) {
        throw new Error(`Estratégia "${page.strategy}" não pertence a este mercado (${market}).`);
      }
      out.push({ ...page, base, quote: page.quote ?? "USDT" });
    } else if (previous) {
      out.push({ ...previous, base, quote: previous.quote ?? "USDT" });
    } else {
      out.push({ ...page, base, quote: page.quote ?? "USDT" });
    }
  }
  return out;
}

function buildSlotsForMarket(
  saved: PaperSlotConfig[] | undefined,
  market: StrategyMarket,
): PaperSlotConfig[] {
  return normalizeSavedSlots(saved, market);
}

function StrategyTable({
  title,
  subtitle,
  badge,
  items,
  slots,
  activeId,
  timeframe,
  setTimeframe,
  onActivate,
  activatePending,
  botRunning,
}: {
  title: string;
  subtitle: string;
  badge: ReactNode;
  items: Strategy[];
  slots: PaperSlotConfig[];
  activeId?: string;
  timeframe: OperationalTimeframe;
  setTimeframe: (tf: OperationalTimeframe) => void;
  onActivate: (id: string) => void;
  activatePending: boolean;
  botRunning?: boolean;
}) {
  if (!items.length) return null;
  return (
    <Panel title={title} subtitle={subtitle} action={badge}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[11px] uppercase tracking-wider text-muted-foreground">
            <tr className="text-left">
              <th className="px-3 py-2 font-medium">Nome</th>
              <th className="px-3 py-2 font-medium">Tipo</th>
              <th className="px-3 py-2 font-medium text-right">Trades</th>
              <th className="px-3 py-2 font-medium text-right">Win Rate</th>
              <th className="px-3 py-2 font-medium text-right">Profit Factor</th>
              <th className="px-3 py-2 font-medium text-right">Drawdown</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium text-right">Ações</th>
            </tr>
          </thead>
          <tbody>
            {items.map((s) => {
              const sid = s.id || s.name;
              const isActive = activeId === sid;
              const inSlots = slots.some((sl) => sl.enabled && sl.strategy === sid);
              return (
                <tr key={sid} className={`border-t border-white/5 hover:bg-white/[0.03] ${isActive || inSlots ? "bg-primary/5" : ""}`}>
                  <td className="px-3 py-3">
                    <div className="font-medium">{s.name}</div>
                    <div className="text-[11px] text-muted-foreground">{sid}</div>
                  </td>
                  <td className="px-3 py-3 text-xs text-muted-foreground max-w-[140px]">{s.strategy_type || "—"}</td>
                  <td className="px-3 py-3 text-right num">{s.trades ?? 0}</td>
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
                      >
                        <option value="1h" className="text-black bg-white">1H</option>
                        <option value="4h" className="text-black bg-white">4H</option>
                        <option value="1d" className="text-black bg-white">1D</option>
                      </select>
                      <button
                        title={`Definir slot 1 · ${timeframe.toUpperCase()}`}
                        disabled={activatePending || botRunning}
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
  );
}

export function StrategiesMarketPage({ market }: { market: StrategyMarket }) {
  const meta = PAGE_META[market];
  const { data, isPending, error, isError } = useStrategies();
  const settings = useSettings();
  const activate = useUpdateOperational();
  const saveSlots = useUpdateOperationalSlots();
  const [timeframe, setTimeframe] = useState<OperationalTimeframe>("4h");
  const [msg, setMsg] = useState<string | null>(null);
  const [slotsDirty, setSlotsDirty] = useState(false);
  const [slots, setSlots] = useState<PaperSlotConfig[]>(() => buildSlotsForMarket(undefined, market));

  const strategies = settings.data?.operational?.strategies ?? [];
  const maxSlots = settings.data?.operational?.max_slots ?? DEFAULT_MAX_SLOTS;
  const slotsPerBase = settings.data?.operational?.max_slots_per_base ?? SLOTS_PER_BASE;
  const botRunning = settings.data?.system.bot_running;

  const marketItems = data?.items.filter((s) => (s.market_type ?? s.strategy_category) === market) ?? [];
  const allowedIdKey = useMemo(() => {
    const fromApi = marketItems.map((s) => s.id).sort();
    if (fromApi.length > 0) return fromApi.join("|");
    return STRATEGY_IDS_BY_MARKET[market].join("|");
  }, [market, data?.items]);

  const allowedIds = useMemo(() => new Set(allowedIdKey.split("|").filter(Boolean)), [allowedIdKey]);

  const slotOptionsList = useMemo(
    () => strategies.filter((s) => allowedIds.has(s.id)),
    [strategies, allowedIdKey],
  );

  useEffect(() => {
    setSlotsDirty(false);
  }, [market]);

  useEffect(() => {
    if (!settings.data?.operational || slotsDirty) return;
    setSlots(buildSlotsForMarket(settings.data.operational.slots, market));
  }, [settings.data?.operational?.slots, market, slotsDirty]);

  if (!isPending && (isError || !data)) {
    return <div className="text-destructive text-sm">Erro ao carregar estratégias.</div>;
  }
  if (isPending || !data) {
    return <div className="text-muted-foreground text-sm">Carregando estratégias…</div>;
  }

  const activeId = settings.data?.system.strategy_id;
  const enabledCount = slots.filter((s) => s.enabled).length;
  const enabledBtc = slots.filter((s) => s.enabled && (s.base ?? "BTC") === "BTC").length;
  const enabledEth = slots.filter((s) => s.enabled && s.base === "ETH").length;

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
    let merged: PaperSlotConfig[];
    try {
      merged = mergeSlotsForSave(
        slots,
        settings.data?.operational?.slots,
        allowedIds,
        market,
      );
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Erro ao preparar slots");
      return;
    }
    saveSlots.mutate(merged.slice(0, TOTAL_SLOT_ROWS), {
      onSuccess: (data) => {
        setSlotsDirty(false);
        if (data.operational?.slots?.length) {
          setSlots(buildSlotsForMarket(data.operational.slots, market));
        }
        setMsg(
          enabledCount === 0
            ? "Slots salvos — habilite ao menos 1 antes de iniciar o bot."
            : `${enabledCount} estratégia(s) pronta(s) — clique Iniciar Paper no Dashboard.`,
        );
      },
      onError: (e) => setMsg(e instanceof Error ? e.message : "Erro ao salvar slots"),
    });
  };

  const updateSlot = (index: number, patch: Partial<PaperSlotConfig>) => {
    setSlotsDirty(true);
    setSlots((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  };

  const btcSlots = slots.slice(0, SLOTS_PER_BASE);
  const ethSlots = slots.slice(SLOTS_PER_BASE, SLOTS_PER_BASE * 2);

  const renderSlotRow = (slot: PaperSlotConfig, index: number, base: "BTC" | "ETH", slotNum: number) => {
    const strategyValue = slotOptionsList.some((s) => s.id === slot.strategy)
      ? slot.strategy
      : (slotOptionsList[0]?.id ?? DEFAULT_STRATEGY[market]);

    return (
    <div
      key={`${base}-${index}`}
      className={`flex flex-wrap items-center gap-3 rounded-xl border px-4 py-3 ${
        slot.enabled ? "border-primary/30 bg-primary/5" : "border-white/5 bg-white/[0.02]"
      }`}
    >
      <label className="flex items-center gap-2 text-sm cursor-pointer">
        <input
          type="checkbox"
          checked={slot.enabled}
          disabled={botRunning}
          onChange={(e) => updateSlot(index, { enabled: e.target.checked, base, strategy: strategyValue })}
          className="rounded border-white/20"
        />
        <span className="text-muted-foreground w-14">Slot {slotNum}</span>
      </label>
      <select
        value={strategyValue}
        disabled={botRunning || slotOptionsList.length === 0}
        onChange={(e) => updateSlot(index, { strategy: e.target.value, base })}
        className="flex-1 min-w-[180px] rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white"
      >
        {slotOptionsList.map((s) => (
          <option key={s.id} value={s.id} className="text-black bg-white">{s.name}</option>
        ))}
      </select>
      <span className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm font-medium w-14 text-center">
        {base}
      </span>
      <select
        value={slot.timeframe}
        disabled={botRunning}
        onChange={(e) => updateSlot(index, { timeframe: e.target.value as OperationalTimeframe, base })}
        className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm w-24 text-white"
      >
        <option value="1h" className="text-black bg-white">1H</option>
        <option value="4h" className="text-black bg-white">4H</option>
        <option value="1d" className="text-black bg-white">1D</option>
      </select>
      {slot.enabled && (
        <span className="text-xs text-success flex items-center gap-1">
          <Layers className="h-3 w-3" />
          {base} · {slot.timeframe.toUpperCase()}
        </span>
      )}
    </div>
    );
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title={meta.title}
        subtitle={meta.subtitle}
        actions={
          <div className="flex flex-wrap gap-2">
            {PEER_ROUTES[market].map((peer) => (
              <Link
                key={peer.to}
                to={peer.to}
                className="rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10"
              >
                {peer.label}
              </Link>
            ))}
            <Link to="/backtests" className="rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10">
              Backtests
            </Link>
          </div>
        }
      />

      {msg && <p className="text-sm text-secondary">{msg}</p>}
      {botRunning && <p className="text-sm text-warning">Pare o bot antes de alterar slots ou estratégias.</p>}

      <Panel
        title={`Operação paralela · ${slotsPerBase} por moeda (${maxSlots} total)`}
        subtitle={`Até ${slotsPerBase} estratégias ${MARKET_SLOT_LABEL[market]} em BTC e ${slotsPerBase} em ETH. Bull e Bear não podem rodar juntos na mesma moeda.`}
      >
        <div className="space-y-6">
          <div className="space-y-3">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: "#F7931A" }} />
              BTC/USDT · {enabledBtc}/{slotsPerBase} habilitada(s)
            </h3>
            {btcSlots.map((slot, i) => renderSlotRow(slot, i, "BTC", i + 1))}
          </div>
          <div className="space-y-3">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: "#627EEA" }} />
              ETH/USDT · {enabledEth}/{slotsPerBase} habilitada(s)
            </h3>
            {ethSlots.map((slot, i) => renderSlotRow(slot, i + SLOTS_PER_BASE, "ETH", i + 1))}
          </div>
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
            {enabledCount} de {maxSlots} habilitada(s) · BTC {enabledBtc} · ETH {enabledEth}
          </span>
        </div>
      </Panel>

      <StrategyTable
        title={meta.tableTitle}
        subtitle={meta.tableSubtitle}
        badge={meta.badge}
        items={marketItems}
        slots={slots}
        activeId={activeId}
        timeframe={timeframe}
        setTimeframe={setTimeframe}
        onActivate={onActivate}
        activatePending={activate.isPending}
        botRunning={botRunning}
      />
    </div>
  );
}
