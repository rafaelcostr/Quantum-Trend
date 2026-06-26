import { createFileRoute } from "@tanstack/react-router";
import { StrategiesMarketPage } from "@/components/strategies/StrategiesMarketPage";

export const Route = createFileRoute("/estrategias-lateral")({
  head: () => ({ meta: [{ title: "Estratégias Laterais · Quantum-Trend" }] }),
  component: () => <StrategiesMarketPage market="range" />,
});
