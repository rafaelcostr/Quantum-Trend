import { createFileRoute, Link } from "@tanstack/react-router";
import { PageHeader, Panel } from "@/components/ui/page";
import { useSettings, useSystemReset, useTestTelegram, useUpdateKillSwitch, useUpdateNotifications } from "@/lib/queries";
import { ApiError } from "@/lib/api";
import { useState } from "react";
import { Trash2 } from "lucide-react";

export const Route = createFileRoute("/configuracoes")({
  head: () => ({ meta: [{ title: "Configurações · Quantum-Trend" }] }),
  component: Page,
});

function Toggle({ checked, onClick, disabled }: { checked: boolean; onClick?: () => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`relative inline-flex items-center w-11 h-6 rounded-full transition disabled:opacity-50 ${checked ? "bg-gradient-to-r from-[#7C3AED] to-[#3B82F6]" : "bg-white/10"}`}
    >
      <div className={`h-5 w-5 rounded-full bg-white transition ${checked ? "translate-x-5" : "translate-x-0.5"}`} />
    </button>
  );
}

const NOTIF_LABELS: Record<string, string> = {
  email_daily: "Resumo diário por e-mail",
  drawdown_alerts: "Alertas de drawdown",
  strategy_approval: "Aprovação de estratégia",
  terminal_sounds: "Sons no terminal",
  telegram: "Telegram (via .env)",
};

function Page() {
  const { data, isPending, isError } = useSettings();
  const testTelegram = useTestTelegram();
  const killSwitch = useUpdateKillSwitch();
  const notif = useUpdateNotifications();
  const systemReset = useSystemReset();
  const [testMsg, setTestMsg] = useState<string | null>(null);
  const [resetReports, setResetReports] = useState(true);
  const [resetCache, setResetCache] = useState(false);
  const [resetPaper, setResetPaper] = useState(false);
  const [resetMsg, setResetMsg] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);

  if (isPending) return <div className="text-muted-foreground text-sm">Carregando configurações…</div>;
  if (isError || !data) return <div className="text-destructive text-sm">Erro ao carregar configurações.</div>;

  const initials = data.profile.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  return (
    <div className="space-y-8">
      <PageHeader title="Configurações" subtitle="Estratégia ativa, kill switch e preferências do terminal." />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Sistema operacional">
          <div className="flex items-center gap-4 mb-5">
            <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-[#7C3AED] to-[#3B82F6] grid place-items-center text-xl font-bold">{initials}</div>
            <div>
              <div className="font-semibold">{data.profile.name}</div>
              <div className="text-xs text-muted-foreground">{data.profile.email} · {data.profile.plan}</div>
            </div>
          </div>
          <div className="rounded-xl bg-white/[0.03] border border-white/5 p-4 text-sm space-y-2">
            <div className="flex justify-between"><span className="text-muted-foreground">Estratégia</span><span>{data.system.strategy}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Par</span><span>{data.system.symbol}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Gráfico</span><span className="uppercase">{data.system.timeframe}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Poll bot</span><span>{data.system.poll_seconds}s</span></div>
          </div>
          <div className="mt-4 flex flex-wrap gap-3 text-xs">
            <Link to="/estrategias-alta" className="text-secondary hover:underline">Estratégias de Alta →</Link>
            <Link to="/estrategias-baixa" className="text-destructive hover:underline">Estratégias de Baixa →</Link>
            <Link to="/estrategias-lateral" className="text-warning hover:underline">Estratégias Laterais →</Link>
          </div>
        </Panel>

        <Panel title="Kill Switch">
          <p className="text-sm text-muted-foreground mb-4">Bloqueia imediatamente start do bot. Prioridade sobre .env.</p>
          <div className="flex items-center justify-between rounded-xl bg-white/[0.03] border border-white/5 p-4">
            <div>
              <div className="font-medium">{data.system.kill_switch ? "ATIVO — bot bloqueado" : "Inativo"}</div>
              <div className="text-xs text-muted-foreground mt-1">Use em emergência ou manutenção</div>
            </div>
            <Toggle
              checked={data.system.kill_switch}
              disabled={killSwitch.isPending}
              onClick={() => killSwitch.mutate(!data.system.kill_switch)}
            />
          </div>
        </Panel>

        <Panel title="Exchanges Conectadas" className="lg:col-span-2">
          {data.exchanges.map((e) => (
            <div key={e.name} className="flex items-center justify-between border-t border-white/5 first:border-t-0 py-3">
              <div className="flex items-center gap-3">
                <span className={`h-2 w-2 rounded-full ${e.connected ? "bg-success" : "bg-destructive"}`} />
                <div>
                  <div className="text-sm font-medium">{e.name}</div>
                  <div className="text-[11px] text-muted-foreground">{e.connected ? "conectada" : "desconectada"}{e.active ? " · ativa" : ""}</div>
                </div>
              </div>
            </div>
          ))}
        </Panel>

        <Panel title="Telegram" className="lg:col-span-2">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <div className="text-sm font-medium">Alertas de entrada e saída</div>
              <div className="text-xs text-muted-foreground mt-1">
                {data.telegram.configured
                  ? "Configurado via .env"
                  : "Preencha TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env"}
              </div>
            </div>
            <button
              disabled={!data.telegram.configured || testTelegram.isPending}
              onClick={() => {
                setTestMsg(null);
                testTelegram.mutate(undefined, {
                  onSuccess: () => setTestMsg("Mensagem de teste enviada."),
                  onError: () => setTestMsg("Falha ao enviar."),
                });
              }}
              className="rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10 disabled:opacity-50"
            >
              {testTelegram.isPending ? "Enviando…" : "Testar Telegram"}
            </button>
          </div>
          {testMsg && <p className={`text-xs mt-3 ${testMsg.includes("Falha") ? "text-destructive" : "text-success"}`}>{testMsg}</p>}
        </Panel>

        <Panel title="Notificações" className="lg:col-span-2">
          {Object.entries(data.notifications).map(([key, on]) => (
            <div key={key} className="flex items-center justify-between border-t border-white/5 first:border-t-0 py-3">
              <span className="text-sm">{NOTIF_LABELS[key] ?? key}</span>
              <Toggle
                checked={on}
                disabled={key === "telegram" || notif.isPending}
                onClick={() => {
                  if (key === "telegram") return;
                  notif.mutate({ [key]: !on });
                }}
              />
            </div>
          ))}
        </Panel>

        <Panel title="Reset de dados" className="lg:col-span-2">
          <p className="text-sm text-muted-foreground mb-4">
            Apaga resultados de backtest, cache de candles e/ou histórico do paper trading.
            A matriz salva no navegador também é limpa. Esta ação não pode ser desfeita.
          </p>
          <div className="space-y-3 mb-5">
            <label className="flex items-start gap-3 rounded-xl bg-white/[0.03] border border-white/5 p-4 cursor-pointer">
              <input
                type="checkbox"
                checked={resetReports}
                onChange={(e) => setResetReports(e.target.checked)}
                className="mt-1 rounded border-white/20"
              />
              <div>
                <div className="text-sm font-medium">Relatórios de backtest</div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  Remove todos os arquivos em <code className="text-[11px]">data/reports/</code> e a matriz local
                </div>
              </div>
            </label>
            <label className="flex items-start gap-3 rounded-xl bg-white/[0.03] border border-white/5 p-4 cursor-pointer">
              <input
                type="checkbox"
                checked={resetCache}
                onChange={(e) => setResetCache(e.target.checked)}
                className="mt-1 rounded border-white/20"
              />
              <div>
                <div className="text-sm font-medium">Cache OHLCV (candles)</div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  Próximo backtest vai baixar candles de novo — pode demorar
                </div>
              </div>
            </label>
            <label className="flex items-start gap-3 rounded-xl bg-white/[0.03] border border-white/5 p-4 cursor-pointer">
              <input
                type="checkbox"
                checked={resetPaper}
                onChange={(e) => setResetPaper(e.target.checked)}
                className="mt-1 rounded border-white/20"
                disabled={data.system.bot_running}
              />
              <div>
                <div className="text-sm font-medium">Paper trading (demo)</div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  Diário, curva de equity, scores Quantum e contadores de risco
                  {data.system.bot_running ? " — pare o bot antes" : ""}
                </div>
              </div>
            </label>
          </div>

          {!confirmReset ? (
            <button
              type="button"
              disabled={!resetReports && !resetCache && !resetPaper}
              onClick={() => {
                setResetMsg(null);
                setConfirmReset(true);
              }}
              className="inline-flex items-center gap-2 rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-2.5 text-sm font-medium text-destructive hover:bg-destructive/20 disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" />
              Apagar / resetar selecionados
            </button>
          ) : (
            <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 space-y-3">
              <p className="text-sm font-medium text-destructive">Confirmar reset?</p>
              <p className="text-xs text-muted-foreground">
                Os dados marcados serão removidos permanentemente.
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={systemReset.isPending}
                  onClick={() => {
                    systemReset.mutate(
                      {
                        reports: resetReports,
                        ohlcv_cache: resetCache,
                        paper_demo: resetPaper,
                      },
                      {
                        onSuccess: (res) => {
                          setConfirmReset(false);
                          if (res.deleted_count === 0 && res.cleared_count === 0) {
                            setResetMsg(
                              "Nenhum arquivo encontrado para apagar — confirme que a API Python está rodando no mesmo projeto (python -m atlas.cli api).",
                            );
                            return;
                          }
                          setResetMsg(
                            `Reset concluído: ${res.deleted_count} arquivo(s) removido(s)` +
                              (res.cleared_count ? `, ${res.cleared_count} limpo(s)` : "") +
                              ". Backtests e Resultados foram limpos.",
                          );
                        },
                        onError: (err) => {
                          setConfirmReset(false);
                          setResetMsg(
                            err instanceof ApiError ? err.message : "Falha ao resetar dados.",
                          );
                        },
                      },
                    );
                  }}
                  className="rounded-xl bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50"
                >
                  {systemReset.isPending ? "Apagando…" : "Sim, apagar agora"}
                </button>
                <button
                  type="button"
                  disabled={systemReset.isPending}
                  onClick={() => setConfirmReset(false)}
                  className="rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-sm hover:bg-white/10 disabled:opacity-50"
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}
          {resetMsg && (
            <p
              className={`text-xs mt-3 ${
                resetMsg.includes("Falha") ||
                resetMsg.includes("pare") ||
                resetMsg.includes("Nenhum arquivo")
                  ? "text-destructive"
                  : "text-success"
              }`}
            >
              {resetMsg}
            </p>
          )}
        </Panel>
      </div>
    </div>
  );
}
