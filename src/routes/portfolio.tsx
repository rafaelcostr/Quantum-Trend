import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/ui/page";
import { PortfolioView } from "@/components/portfolio/PortfolioView";
import { isBrowser, usePortfolio } from "@/lib/queries";

export const Route = createFileRoute("/portfolio")({
  head: () => ({ meta: [{ title: "Portfolio · Quantum-Trend" }] }),
  component: PortfolioPage,
});

function PortfolioPage() {
  const { data, isPending, error, isError, isFetching } = usePortfolio();

  if (!isBrowser || (isPending && !data)) {
    return (
      <div className="text-muted-foreground text-sm space-y-2 py-12 text-center">
        <p>Carregando portfolio…</p>
        <p className="text-xs opacity-70">Montando curvas, estratégias e health score.</p>
      </div>
    );
  }
  if ((isError && !data) || !data) {
    return (
      <div className="text-destructive text-sm">
        {error instanceof Error ? error.message : "Erro ao carregar portfolio."}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Portfolio"
        subtitle="Visão institucional — patrimônio, drawdown, estratégias, alocação e health score."
      />
      {isFetching && (
        <p className="text-xs text-muted-foreground text-center">Atualizando dados…</p>
      )}
      <PortfolioView data={data} />
    </div>
  );
}
