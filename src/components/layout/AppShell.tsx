import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  FlaskConical,
  BarChart3,
  MonitorPlay,
  LineChart,
  ShieldCheck,
  Bot,
  NotebookPen,
  FileBarChart,
  Globe2,
  Settings,
  Rocket,
  Search,
  Bell,
  ChevronDown,
  Moon,
  Wallet,
  TrendingUp,
  TrendingDown,
  ArrowLeftRight,
  Microscope,
} from "lucide-react";
import type { ReactNode } from "react";
import { BotUptimeTimer } from "@/components/operations/BotUptimeTimer";
import { useBotStatus, useHealth, useSettings } from "@/lib/queries";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/estrategias-alta", label: "Estratégias de Alta", icon: TrendingUp },
  { to: "/estrategias-baixa", label: "Estratégias de Baixa", icon: TrendingDown },
  { to: "/estrategias-lateral", label: "Estratégias Laterais", icon: ArrowLeftRight },
  { to: "/backtests", label: "Backtests", icon: FlaskConical },
  { to: "/laboratorio", label: "Laboratório Quant", icon: Microscope },
  { to: "/validacao", label: "Paper", icon: MonitorPlay },
  { to: "/portfolio", label: "Portfolio", icon: Wallet },
  { to: "/resultados", label: "Resultados", icon: BarChart3 },
  { to: "/live", label: "Live", icon: Rocket },
  { to: "/operacoes", label: "Operações", icon: LineChart },
  { to: "/risco", label: "Risco", icon: ShieldCheck },
  { to: "/diario", label: "Journal", icon: NotebookPen },
  { to: "/relatorios", label: "Relatórios", icon: FileBarChart },
  { to: "/mercados", label: "Mercados", icon: Globe2 },
  { to: "/ia", label: "IA de Seleção", icon: Bot },
  { to: "/configuracoes", label: "Configurações", icon: Settings },
] as const;

function Sidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const bot = useBotStatus();
  const running = bot.data?.running ?? false;
  const mode = bot.data?.mode ?? "paper";
  const instanceCount = bot.data?.instance_count ?? 0;
  const modeLabel = mode === "live" ? "Live · Binance Real" : "Paper · Binance Demo";
  return (
    <aside className="hidden lg:flex fixed left-0 top-0 z-40 h-screen w-64 flex-col glass border-r border-white/5 px-4 py-6">
      <Link to="/" className="flex items-center gap-2.5 px-2 mb-8">
        <div className="relative h-9 w-9 rounded-xl bg-gradient-to-br from-[#7C3AED] to-[#3B82F6] glow-primary flex items-center justify-center">
          <span className="text-white font-bold text-sm">Q</span>
        </div>
        <div className="leading-tight">
          <div className="text-[15px] font-semibold tracking-tight">Quantum</div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            Trend Terminal
          </div>
        </div>
      </Link>
      <nav className="flex flex-col gap-1 overflow-y-auto pr-1">
        {NAV.map((item) => {
          const active = pathname === item.to || (item.to !== "/" && pathname.startsWith(item.to));
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`relative group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all ${
                active
                  ? "bg-gradient-to-r from-[#7C3AED]/25 to-[#3B82F6]/10 text-white border border-white/10"
                  : "text-muted-foreground hover:text-white hover:bg-white/5"
              }`}
            >
              {active && (
                <span className="absolute left-0 h-5 w-1 rounded-r bg-gradient-to-b from-[#7C3AED] to-[#3B82F6]" />
              )}
              <Icon className="h-4 w-4" />
              <span className="font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto pt-4">
        <div className="glass-strong rounded-2xl p-4">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span
              className={`h-2 w-2 rounded-full ${running ? (mode === "live" ? "bg-destructive" : "bg-success animate-pulse") : "bg-muted-foreground"}`}
            />
            {running
              ? mode === "live"
                ? "Bot LIVE"
                : instanceCount > 1
                  ? `${instanceCount} bots paper`
                  : "Bot paper"
              : "Bot parado"}
          </div>
          <div className="mt-2 num text-xl">
            {running ? (
              <BotUptimeTimer
                startedAt={bot.data?.started_at}
                running={running}
                className="text-xl font-semibold text-success"
              />
            ) : (
              "—"
            )}
          </div>
          <div className="text-[11px] text-muted-foreground">
            {running ? (
              <>
                Tempo ligado
                {instanceCount > 1 ? ` · ${instanceCount} engines` : ""}
              </>
            ) : (
              modeLabel
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}

function Topbar() {
  const { data: settings } = useSettings();
  const health = useHealth();
  const active = settings?.exchanges?.find((e) => e.active);
  const accountLabel = active?.name ?? "Binance Demo";
  const binanceOk = active?.connected ?? false;
  const apiOk = health.isSuccess && health.data?.status === "ok";
  const apiError = health.isError;

  return (
    <header className="sticky top-0 z-30 glass border-b border-white/5 backdrop-blur-xl">
      <div className="flex items-center gap-3 px-6 lg:px-10 h-16">
        <div className="relative flex-1 max-w-md hidden md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            placeholder="Buscar ativo, estratégia, ordem..."
            className="w-full rounded-xl bg-white/5 border border-white/10 pl-10 pr-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition"
          />
        </div>
        <div className="ml-auto flex items-center gap-2 flex-wrap justify-end">
          <span
            className="hidden sm:flex items-center gap-2 rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-[11px]"
            title="FastAPI Python"
          >
            <span
              className={`h-2 w-2 rounded-full ${apiOk ? "bg-success" : apiError ? "bg-destructive" : "bg-warning animate-pulse"}`}
            />
            API {apiOk ? "OK" : apiError ? "offline" : "…"}
          </span>
          <button className="hidden md:flex items-center gap-2 rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-xs hover:bg-white/10 transition">
            <span
              className={`h-2 w-2 rounded-full ${binanceOk ? "bg-success" : "bg-destructive"}`}
            />
            {accountLabel}
            {settings?.system.timeframe && (
              <span className="text-muted-foreground">
                · {settings.system.timeframe.toUpperCase()}
              </span>
            )}
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
          <button className="h-9 w-9 grid place-items-center rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition">
            <Moon className="h-4 w-4" />
          </button>
          <button className="relative h-9 w-9 grid place-items-center rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition">
            <Bell className="h-4 w-4" />
            <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-primary animate-pulse" />
          </button>
          <div className="flex items-center gap-2.5 rounded-xl bg-white/5 border border-white/10 px-2 py-1.5">
            <div className="h-7 w-7 rounded-full bg-gradient-to-br from-[#7C3AED] to-[#3B82F6] grid place-items-center text-xs font-semibold">
              QT
            </div>
            <div className="hidden sm:block leading-tight pr-1">
              <div className="text-xs font-medium">{settings?.profile.name ?? "Operador"}</div>
              <div className="text-[10px] text-muted-foreground">
                {settings?.profile.plan ?? "Atlas Paper"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <Sidebar />
      <div className="lg:pl-64">
        <Topbar />
        <main className="px-6 lg:px-10 py-8">
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">{children}</div>
        </main>
      </div>
    </div>
  );
}
