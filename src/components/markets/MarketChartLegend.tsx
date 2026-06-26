import { CHART_INDICATOR_LEGEND, STRATEGY_CHART_GUIDE, type StrategyChartGuide } from "@/lib/tradingview-chart";
import { cn } from "@/lib/utils";

const CATEGORY_LABEL: Record<StrategyChartGuide["category"], string> = {
  core: "Core",
  bull: "Alta",
  bear: "Baixa",
  range: "Lateral",
};

const CATEGORY_STYLE: Record<StrategyChartGuide["category"], string> = {
  core: "border-primary/40 bg-primary/10 text-primary",
  bull: "border-success/30 bg-success/10 text-success",
  bear: "border-destructive/30 bg-destructive/10 text-destructive",
  range: "border-sky-500/30 bg-sky-500/10 text-sky-300",
};

export function MarketChartLegend() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 border-t border-white/5 p-4">
      <div>
        <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-3">Indicadores no gráfico</div>
        <ul className="space-y-2">
          {CHART_INDICATOR_LEGEND.map((item) => (
            <li key={item.key} className="flex items-start gap-3 text-xs">
              <span className={cn("mt-1 h-0.5 w-8 shrink-0 rounded", item.color)} />
              <div>
                <div className="font-medium text-foreground">{item.label}</div>
                <div className="text-muted-foreground">{item.hint}</div>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-3">Estratégias · indicadores usados</div>
        <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
          {STRATEGY_CHART_GUIDE.map((s) => (
            <div key={s.id} className="rounded-xl border border-white/10 bg-white/[0.02] px-3 py-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-medium">{s.label}</span>
                <span className={cn("text-[10px] px-1.5 py-0.5 rounded border", CATEGORY_STYLE[s.category])}>
                  {CATEGORY_LABEL[s.category]}
                </span>
              </div>
              <div className="mt-1.5 flex flex-wrap gap-1">
                {s.indicators.map((ind) => (
                  <span key={ind} className="text-[10px] rounded-md bg-white/5 border border-white/10 px-1.5 py-0.5 text-muted-foreground">
                    {ind}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
