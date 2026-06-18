import { createFileRoute, Link } from "@tanstack/react-router";
import { PageHeader, Panel } from "@/components/ui/page";
import { OperationsFeed } from "@/components/widgets/OperationsFeed";
import { useBotToggle, useDashboard, useOperationsFeed, usePositions } from "@/lib/queries";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

export const Route = createFileRoute("/operacoes")({
  head: () => ({ meta: [{ title: "Operações · Quantum-Trend" }] }),
  component: Page,
});

function Page() {
  const pos = usePositions();
  const dash = useDashboard();
  const feed = useOperationsFeed();
  const bot = useBotToggle();

  if (pos.isLoading || dash.isLoading || feed.isLoading) {
    return <div className="text-muted-foreground text-sm">Carregando mesa ao vivo…</div>;
  }
  if (pos.error || dash.error || !pos.data || !dash.data) {
    return <div className="text-destructive text-sm">Erro ao carregar operações.</div>;
  }

  const positions = pos.data.items;
  const sel = positions[0];
  const equity = dash.data.equity_curve.slice(-30);
  const running = feed.data?.bot.running ?? dash.data.stats.bot_running;
  const mode = feed.data?.mode ?? dash.data.stats.bot_mode ?? "paper";

  return (
    <div className="space-y-8">
      <PageHeader
        title="Operações ao Vivo"
        subtitle={
          running
            ? `Mesa ${mode === "live" ? "LIVE · capital real" : "PAPER · Binance Demo"} · feed atualiza a cada 3s.`
            : "Inicie o bot para acompanhar ticks, sinais e execuções em tempo real."
        }
        actions={
          <div className="flex gap-2">
            <Link to="/live" className="rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10">
              Trading Live
            </Link>
            <button
              onClick={() => bot.mutate(running ? "stop" : "start")}
              disabled={bot.isPending || dash.data.stats.kill_switch}
              className={`rounded-xl px-4 py-2 text-sm font-medium disabled:opacity-50 ${
                running
                  ? "bg-destructive/90 text-white"
                  : "bg-gradient-to-r from-[#7C3AED] to-[#3B82F6] text-white"
              }`}
            >
              {running ? "Parar Bot" : "Iniciar Paper"}
            </button>
          </div>
        }
      />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Panel className="xl:col-span-2" title="Feed em tempo real" action={<span className="chip text-success">{feed.isStreaming ? "SSE" : "poll"}</span>}>
          {feed.data ? (
            <OperationsFeed data={feed.data} />
          ) : (
            <p className="text-sm text-muted-foreground">Feed indisponível — reinicie a API Python.</p>
          )}
        </Panel>

        <Panel title="Posições Abertas">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr className="text-left">
                  <th className="px-2 py-2 font-medium">Ativo</th>
                  <th className="px-2 py-2 font-medium text-right">P&L</th>
                </tr>
              </thead>
              <tbody>
                {positions.length === 0 ? (
                  <tr><td colSpan={2} className="py-6 text-center text-muted-foreground text-xs">Sem posição</td></tr>
                ) : positions.map((p, i) => {
                  const up = p.pnl >= 0;
                  return (
                    <tr key={i} className="border-t border-white/5">
                      <td className="px-2 py-2"><span className="font-medium">{p.asset}</span> <span className="chip text-xs">{p.side}</span></td>
                      <td className={`px-2 py-2 text-right num ${up ? "text-success" : "text-destructive"}`}>{up ? "+" : ""}${p.pnl.toFixed(2)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {sel && (
            <div className="mt-4 pt-4 border-t border-white/5">
              <div className="num text-2xl">${sel.current.toLocaleString()}</div>
              <div className={`text-xs mt-1 ${sel.pnl >= 0 ? "text-success" : "text-destructive"}`}>
                {sel.pnl >= 0 ? "+" : ""}{sel.pnl_pct.toFixed(2)}% · ${sel.pnl.toFixed(2)}
              </div>
              <div className="h-24 mt-3">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={equity}>
                    <defs>
                      <linearGradient id="oc" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#22C55E" stopOpacity={0.5} />
                        <stop offset="100%" stopColor="#22C55E" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Area type="monotone" dataKey="equity" stroke="#22C55E" strokeWidth={2} fill="url(#oc)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
