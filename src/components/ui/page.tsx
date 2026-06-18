import type { ReactNode } from "react";

export function PageHeader({
  title, subtitle, actions,
}: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <div className="mt-1.5 text-sm text-muted-foreground max-w-2xl">{subtitle}</div>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Panel({
  children, className = "", title, subtitle, action,
}: { children: ReactNode; className?: string; title?: string; subtitle?: string; action?: ReactNode }) {
  return (
    <section className={`glass rounded-2xl p-6 ${className}`}>
      {(title || subtitle || action) && (
        <header className="flex items-center justify-between mb-5">
          <div>
            {title && <h2 className="text-sm font-semibold tracking-wide uppercase text-muted-foreground">{title}</h2>}
            {subtitle && <p className="mt-1 text-xs text-muted-foreground/80">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
