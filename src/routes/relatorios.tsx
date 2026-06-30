import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { PageHeader, Panel } from "@/components/ui/page";
import { InlineError, LoadingBlock } from "@/components/ui/query-state";
import { Download } from "lucide-react";
import { useReports } from "@/lib/queries";

const ReportsCharts = lazy(() =>
  import("@/components/reports/ReportsCharts").then((module) => ({
    default: module.ReportsCharts,
  })),
);

export const Route = createFileRoute("/relatorios")({
  head: () => ({ meta: [{ title: "Relatórios · Quantum-Trend" }] }),
  component: Page,
});

function Page() {
  const { data, isLoading, error } = useReports();
  if (isLoading) return <LoadingBlock label="Carregando relatórios..." />;
  if (error || !data) return <InlineError error={error} title="Erro ao carregar relatórios" />;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Relatórios"
        subtitle="Relatórios consolidados do backtest Atlas."
        actions={
          <button className="inline-flex items-center gap-2 rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10">
            <Download className="h-4 w-4" /> Exportar PDF
          </button>
        }
      />

      <Suspense fallback={<LoadingBlock label="Preparando gráficos dos relatórios..." />}>
        <ReportsCharts data={data} />
      </Suspense>

      <Panel title="Resumo">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          {data.summary.map(([l, v, c]) => (
            <div key={l} className="rounded-xl bg-white/[0.03] border border-white/5 p-4">
              <div className="text-xs text-muted-foreground">{l}</div>
              <div className={`num text-xl mt-1 ${c}`}>{v}</div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
