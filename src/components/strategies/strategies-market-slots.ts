import type { PaperSlotConfig } from "@/lib/api";

export type StrategyMarket = "bull" | "bear" | "range";

export const DEFAULT_STRATEGY: Record<StrategyMarket, string> = {
  bull: "pullback_ema20_v1",
  bear: "pullback_short_v1",
  range: "range_hunter_v1",
};

export const SLOTS_PER_BASE = 6;
export const TREND_SLOTS_PER_BASE = 3;
export const LATERAL_SLOTS_EDITABLE = 2;
export const TOTAL_SLOT_ROWS = SLOTS_PER_BASE * 2;

export const PANEL_SLOT_HINT: Record<StrategyMarket, string> = {
  bull: "6 estratégias de alta por moeda. Se existir qualquer Baixa ativa no bot, esta página inteira fica bloqueada (e vice-versa). Laterais são independentes.",
  bear: "6 estratégias de baixa por moeda. Se existir qualquer Alta ativa no bot, esta página inteira fica bloqueada (e vice-versa). Laterais são independentes.",
  range:
    "6 estratégias laterais por moeda. Slots 4 e 5 ficam livres mesmo com Alta nos slots 1–2. Demais slots com tendência ativa aparecem somente leitura.",
};

export const STRATEGY_IDS_BY_MARKET: Record<StrategyMarket, string[]> = {
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

function localIndex(globalIdx: number): number {
  return globalIdx % SLOTS_PER_BASE;
}

export function isFirstLateralSlot(globalIdx: number): boolean {
  const local = localIndex(globalIdx);
  return local >= TREND_SLOTS_PER_BASE && local < TREND_SLOTS_PER_BASE + LATERAL_SLOTS_EDITABLE;
}

export function indicesForBase(base: "BTC" | "ETH"): number[] {
  const offset = base === "BTC" ? 0 : SLOTS_PER_BASE;
  return Array.from({ length: SLOTS_PER_BASE }, (_, i) => offset + i);
}

export function strategyMarketType(strategy: string): StrategyMarket | null {
  if (STRATEGY_IDS_BY_MARKET.bear.includes(strategy)) return "bear";
  if (STRATEGY_IDS_BY_MARKET.range.includes(strategy)) return "range";
  if (STRATEGY_IDS_BY_MARKET.bull.includes(strategy)) return "bull";
  return null;
}

export function slotBelongsToMarket(
  strategy: string,
  market: StrategyMarket,
  allowedIds: Set<string>,
): boolean {
  return allowedIds.has(strategy) || STRATEGY_IDS_BY_MARKET[market].includes(strategy);
}

export function countEnabledByType(slots: PaperSlotConfig[], type: StrategyMarket): number {
  return slots.filter((s) => s.enabled && strategyMarketType(s.strategy) === type).length;
}

export function oppositeTrendActive(slots: PaperSlotConfig[], market: StrategyMarket): boolean {
  if (market === "bull") return countEnabledByType(slots, "bear") > 0;
  if (market === "bear") return countEnabledByType(slots, "bull") > 0;
  return false;
}

export function oppositeTrendLockMessage(market: StrategyMarket): string {
  if (market === "bull") {
    return "Baixa ativa no bot — desabilite todas em Estratégias de Baixa para editar Alta.";
  }
  return "Alta ativa no bot — desabilite todas em Estratégias de Alta para editar Baixa.";
}

export function slotLockReason(
  globalIdx: number,
  market: StrategyMarket,
  slot: PaperSlotConfig,
  allSlots: PaperSlotConfig[],
): string | null {
  if (market === "range") {
    if (isFirstLateralSlot(globalIdx)) return null;
    if (!slot.enabled) return null;
    const st = strategyMarketType(slot.strategy);
    if (!st || st === "range") return null;
    if (st === "bull") return "Alta ativa neste slot — edite em Estratégias de Alta.";
    if (st === "bear") return "Baixa ativa neste slot — edite em Estratégias de Baixa.";
    return null;
  }

  if ((market === "bull" || market === "bear") && oppositeTrendActive(allSlots, market)) {
    const st = strategyMarketType(slot.strategy);
    if (slot.enabled && st === market) return null;
    return oppositeTrendLockMessage(market);
  }

  if (!slot.enabled) return null;
  const st = strategyMarketType(slot.strategy);
  if (!st || st === market) return null;
  if (st === "bull") return "Alta ativa neste slot — edite em Estratégias de Alta.";
  if (st === "bear") return "Baixa ativa neste slot — edite em Estratégias de Baixa.";
  return "Lateral ativa neste slot — edite em Estratégias Laterais.";
}

export function isSlotLocked(
  globalIdx: number,
  market: StrategyMarket,
  slot: PaperSlotConfig,
  allSlots: PaperSlotConfig[],
): boolean {
  return slotLockReason(globalIdx, market, slot, allSlots) !== null;
}

export function slotLabel(globalIdx: number): number {
  return (globalIdx % SLOTS_PER_BASE) + 1;
}

export const emptySlot = (market: StrategyMarket, base: "BTC" | "ETH"): PaperSlotConfig => ({
  strategy: DEFAULT_STRATEGY[market],
  timeframe: "4h",
  quote: "USDT",
  base,
  enabled: false,
});

export function slotBaseAtIndex(globalIdx: number): "BTC" | "ETH" {
  return globalIdx < SLOTS_PER_BASE ? "BTC" : "ETH";
}

function normalizeRangeSlotForSave(slot: PaperSlotConfig): PaperSlotConfig {
  if (!slot.enabled) return slot;
  const st = strategyMarketType(slot.strategy);
  if (st === "range") return slot;
  return { ...slot, strategy: DEFAULT_STRATEGY.range };
}

export function normalizeSavedSlots(
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

export function mergeSlotsForSave(
  pageSlots: PaperSlotConfig[],
  saved: PaperSlotConfig[] | undefined,
  allowedIds: Set<string>,
  market: StrategyMarket,
  dirtyIndices: ReadonlySet<number>,
): PaperSlotConfig[] {
  const prev = normalizeSavedSlots(saved, market);
  const out: PaperSlotConfig[] = [];

  if (market === "bull" && oppositeTrendActive(prev, "bull")) {
    const enablingBull = [...dirtyIndices].some((idx) => {
      const page = pageSlots[idx];
      return page.enabled && strategyMarketType(page.strategy) === "bull";
    });
    if (enablingBull) throw new Error(oppositeTrendLockMessage("bull"));
  }
  if (market === "bear" && oppositeTrendActive(prev, "bear")) {
    const enablingBear = [...dirtyIndices].some((idx) => {
      const page = pageSlots[idx];
      return page.enabled && strategyMarketType(page.strategy) === "bear";
    });
    if (enablingBear) throw new Error(oppositeTrendLockMessage("bear"));
  }

  for (let globalIdx = 0; globalIdx < TOTAL_SLOT_ROWS; globalIdx++) {
    const base = slotBaseAtIndex(globalIdx);
    const page = pageSlots[globalIdx] ?? emptySlot(market, base);
    const baseline = prev[globalIdx] ?? emptySlot(market, base);

    if (!dirtyIndices.has(globalIdx)) {
      out.push({ ...baseline, base, quote: baseline.quote ?? "USDT" });
      continue;
    }

    let toSave = page;
    if (toSave.enabled) {
      const st = strategyMarketType(toSave.strategy);
      if (market === "range" && isFirstLateralSlot(globalIdx)) {
        toSave = normalizeRangeSlotForSave(toSave);
      } else if (st && st !== market) {
        throw new Error(
          `Este slot está configurado para ${st} — desabilite na página correspondente antes de alterar aqui.`,
        );
      }
      if (!slotBelongsToMarket(toSave.strategy, market, allowedIds)) {
        throw new Error(`Estratégia "${toSave.strategy}" não pertence a este mercado (${market}).`);
      }
    }
    out.push({ ...toSave, base, quote: toSave.quote ?? "USDT" });
  }
  return out;
}

export function buildSlotsForMarket(
  saved: PaperSlotConfig[] | undefined,
  market: StrategyMarket,
): PaperSlotConfig[] {
  const rows = normalizeSavedSlots(saved, market);

  return rows.map((slot, idx) => {
    const base = slotBaseAtIndex(idx);
    const st = strategyMarketType(slot.strategy);
    if (market === "range" && isFirstLateralSlot(idx) && !slot.enabled && st && st !== "range") {
      return emptySlot(market, base);
    }
    if (!slot.enabled && st && st !== market) {
      return emptySlot(market, base);
    }
    return slot;
  });
}
