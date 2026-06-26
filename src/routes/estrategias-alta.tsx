import { createFileRoute } from "@tanstack/react-router";
import { StrategiesMarketPage } from "@/components/strategies/StrategiesMarketPage";

export const Route = createFileRoute("/estrategias-alta")({
  head: () => ({ meta: [{ title: "Estratégias de Alta · Quantum-Trend" }] }),
  component: () => <StrategiesMarketPage market="bull" />,
});
