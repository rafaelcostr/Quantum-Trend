import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/ui/page";
import { PortfolioView } from "@/components/portfolio/PortfolioView";
import { InlineError, LoadingBlock } from "@/components/ui/query-state";
import { isBrowser, usePortfolio } from "@/lib/queries";

export const Route = createFileRoute("/portfolio")({
  head: () => ({ meta: [{ title: "Portfolio · Quantum-Trend" }] }),
  component: PortfolioPage,
});

function PortfolioPage() {
  const { data, isPending, error, isError, isFetching } = usePortfolio();

  if (!isBrowser || (isPending && !data)) {
    return <LoadingBlock label="Montando portfólio, curvas e health score..." />;
  }
  if ((isError && !data) || !data) {
    return <InlineError error={error} title="Erro ao carregar portfólio" />;
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
