import type { BacktestAllProgress, OperatedBase } from "./api";

/** Resolve o ativo em execução a partir do job (API nova ou legada). */
export function resolveRunningAsset(
  progress: BacktestAllProgress | null | undefined,
): OperatedBase | null {
  if (!progress) return null;

  const explicit = progress.base_asset;
  if (explicit === "BTC" || explicit === "ETH") return explicit;

  const fromLabel = progress.asset_label?.split("/")[0]?.toUpperCase();
  if (fromLabel === "BTC" || fromLabel === "ETH") return fromLabel;

  const current = progress.current ?? "";
  if (current.startsWith("ETH ·") || current.includes("ETH/")) return "ETH";
  if (current.startsWith("BTC ·") || current.includes("BTC/")) return "BTC";

  return null;
}

export function resolveRunningLabel(
  progress: BacktestAllProgress | null | undefined,
): string | null {
  if (!progress) return null;
  if (progress.asset_label) return progress.asset_label;
  const asset = resolveRunningAsset(progress);
  return asset ? `${asset}/USDT` : null;
}
