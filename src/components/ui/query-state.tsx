import type { ReactNode } from "react";
import { AlertTriangle, Clock3, Loader2, WifiOff } from "lucide-react";
import type { ApiExternalError } from "@/lib/api";
import { cn } from "@/lib/utils";

export function formatApiError(error: unknown): string {
  if (!error) return "Erro desconhecido.";
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  if (typeof error === "object" && error !== null) {
    const payload = error as ApiExternalError;
    return payload.message ?? payload.kind ?? "Erro externo.";
  }
  return "Erro desconhecido.";
}

export function LoadingBlock({ label = "Carregando dados..." }: { label?: string }) {
  return (
    <div className="flex min-h-[180px] flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="h-5 w-5 animate-spin" />
      {label}
    </div>
  );
}

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="rounded-xl border border-dashed border-white/15 bg-white/[0.02] px-6 py-8 text-center">
      <div className="text-sm font-medium">{title}</div>
      {detail && <div className="mt-1 text-xs text-muted-foreground">{detail}</div>}
    </div>
  );
}

export function InlineError({
  error,
  title = "Falha ao carregar dados",
  className,
}: {
  error?: unknown;
  title?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-xl border border-destructive/35 bg-destructive/10 px-4 py-3 text-sm text-destructive",
        className,
      )}
    >
      <WifiOff className="mt-0.5 h-5 w-5 shrink-0" />
      <div>
        <div className="font-medium">{title}</div>
        <div className="mt-1 text-xs opacity-90">{formatApiError(error)}</div>
      </div>
    </div>
  );
}

export function StaleBadge({
  stale,
  lastSuccessAt,
  className,
}: {
  stale?: boolean;
  lastSuccessAt?: string | null;
  className?: string;
}) {
  if (!stale) return null;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg border border-warning/35 bg-warning/10 px-2.5 py-1 text-[11px] font-medium text-warning",
        className,
      )}
      title={lastSuccessAt ? `Última atualização válida: ${lastSuccessAt}` : undefined}
    >
      <Clock3 className="h-3.5 w-3.5" />
      Dado cacheado
    </span>
  );
}

export function WarningState({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-xl border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
      <div>{children}</div>
    </div>
  );
}
