import { createFileRoute } from "@tanstack/react-router";
import { PageHeader, Panel } from "@/components/ui/page";
import { isBrowser, useMarkets } from "@/lib/queries";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

export const Route = createFileRoute("/mercados")({
  head: () => ({ meta: [{ title: "Mercados · Quantum-Trend" }] }),
  component: Page,
});

function Page() {
  const { data, isPending, error, isError } = useMarkets();

  if (!isBrowser || isPending) {
    return <div className="text-muted-foreground text-sm">Carregando mercados…</div>;
  }
  if (isError || !data) {
    const msg = error instanceof Error ? error.message : "Erro desconhecido";
    return (
      <div className="text-destructive text-sm space-y-2">
        <p>Erro ao carregar mercados. Confirme que a API Python está ativa (<code className="text-secondary">python -m atlas.cli api</code>).</p>
        <p className="text-xs text-muted-foreground">{msg.slice(0, 240)}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader title="Mercados" subtitle="Cobertura global em tempo real — spot via Binance." />

      <Panel>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {data.items.map((a) => {
            const up = a.change_pct >= 0;
            const color = up ? "#22C55E" : "#EF4444";
            const chartData = a.sparkline.map((y, j) => ({ x: j, y }));
            return (
              <div key={a.symbol} className="glass rounded-2xl p-4 hover:scale-[1.02] transition">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold">{a.symbol}/USDT</div>
                    <div className="text-[11px] text-muted-foreground">Spot · Binance</div>
                  </div>
                  <span className={`chip ${up ? "text-success" : "text-destructive"}`}>
                    {up ? "+" : ""}{a.change_pct.toFixed(2)}%
                  </span>
                </div>
                <div className="num text-2xl mt-3">${a.price.toLocaleString(undefined, { maximumFractionDigits: a.price < 1 ? 4 : 2 })}</div>
                <div className="h-14 mt-2 -mx-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id={`m-${a.symbol}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={color} stopOpacity={0.45} />
                          <stop offset="100%" stopColor={color} stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <Area type="monotone" dataKey="y" stroke={color} strokeWidth={2} fill={`url(#m-${a.symbol})`} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}
