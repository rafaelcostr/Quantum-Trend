import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/ui/page";
import { PortfolioView } from "@/components/portfolio/PortfolioView";
import { isBrowser, usePortfolio } from "@/lib/queries";

export const Route = createFileRoute("/portfolio")({
  head: () => ({ meta: [{ title: "Portfolio · Quantum-Trend" }] }),
  component: PortfolioPage,
});

function PortfolioPage() {
  const { data, isPending, error, isError } = usePortfolio();

  if (!isBrowser || isPending) {
    return (
      <div className="text-muted-foreground text-sm space-y-2 py-12 text-center">
        <p>Carregando portfolio…</p>
        <p className="text-xs opacity-70">Montando curvas, estratégias e health score.</p>
      </div>
    );
  }
  if (isError || !data) {
    return <div className="text-destructive text-sm">{error instanceof Error ? error.message : "Erro ao carregar portfolio."}</div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Portfolio"
        subtitle="Visão institucional — patrimônio, drawdown, estratégias, alocação e health score."
      />
      <PortfolioView data={data} />
    </div>
  );
}
