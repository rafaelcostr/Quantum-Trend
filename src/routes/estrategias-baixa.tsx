import { createFileRoute } from "@tanstack/react-router";
import { StrategiesMarketPage } from "@/components/strategies/StrategiesMarketPage";

export const Route = createFileRoute("/estrategias-baixa")({
  head: () => ({ meta: [{ title: "Estratégias de Baixa · Quantum-Trend" }] }),
  component: () => <StrategiesMarketPage market="bear" />,
});
