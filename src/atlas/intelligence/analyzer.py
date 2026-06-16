from __future__ import annotations

from pathlib import Path
from typing import Any

from atlas.intelligence.confidence import confidence_level
from atlas.intelligence.diagnostics import (
    build_diagnostics,
    overfitting_risk_l1,
    promotion_checklist_backtest_paper,
)
from atlas.intelligence.metrics import (
    ReportBundle,
    compute_cagr,
    load_report,
    period_bounds,
    years_tested,
)
from atlas.intelligence.level2_diagnostics import build_level2_narrative
from atlas.intelligence.level2_glossary import build_educational_metrics
from atlas.intelligence.level2_metrics import build_level2_values
from atlas.intelligence.level3_diagnostics import build_level3_narrative, overfitting_risk_l3
from atlas.intelligence.level3_glossary import build_level3_educational_metrics
from atlas.intelligence.level3_metrics import build_level3_values
from atlas.intelligence.models import (
    Level1Snapshot,
    Level2Snapshot,
    Level3Snapshot,
    MetricReading,
    StrategyAnalysis,
)
from atlas.intelligence.research_store import load_walkforward
from atlas.intelligence.score import build_level1_metrics, compute_atlas_score, score_label


def analyze_report(
    bundle: ReportBundle,
    *,
    market: str = "BTC/USDT",
    timeframe: str = "4h",
    source: str = "backtest",
    buy_hold_pct: float | None = None,
    walkforward: dict[str, Any] | None = None,
) -> StrategyAnalysis:
    metrics, values = build_level1_metrics(bundle)
    cagr = compute_cagr(bundle.equity_curve, values["net_profit_pct"])
    values["cagr"] = cagr

    yrs = years_tested(bundle.equity_curve)
    conf_label, conf_emoji, conf_sub = confidence_level(
        total_trades=int(values["total_trades"]),
        profit_factor=values["profit_factor"],
        sharpe=values.get("sharpe_ratio"),
        max_drawdown_pct=values["max_drawdown_pct"],
        years_tested=yrs,
    )

    atlas_score = compute_atlas_score(
        max_drawdown_pct=values["max_drawdown_pct"],
        profit_factor=values["profit_factor"],
        expectancy_pct=values["expectancy_pct"],
        sharpe=values.get("sharpe_ratio"),
        net_profit_pct=values["net_profit_pct"],
        total_trades=int(values["total_trades"]),
        confidence_subscore=conf_sub,
    )
    score_lbl, score_emoji = score_label(atlas_score)

    of_label, of_emoji = overfitting_risk_l1(
        total_trades=int(values["total_trades"]),
        profit_factor=values["profit_factor"],
        max_drawdown_pct=values["max_drawdown_pct"],
        net_profit_pct=values["net_profit_pct"],
        buy_hold_pct=buy_hold_pct,
    )

    strengths, weaknesses, risks, summary = build_diagnostics(values, buy_hold_pct=buy_hold_pct)

    score_metric = MetricReading(
        key="atlas_score",
        label="Atlas Score",
        value=atlas_score,
        display=f"{atlas_score:.0f}",
        status="excellent" if atlas_score >= 80 else "acceptable" if atlas_score >= 60 else "poor",
        emoji=score_emoji,
        status_text=score_lbl,
    )
    conf_metric = MetricReading(
        key="confidence",
        label="Confiança",
        value=None,
        display=conf_label,
        status="excellent" if "Alta" in conf_label else "acceptable" if "Média" in conf_label else "poor",
        emoji=conf_emoji,
        status_text=conf_label,
    )

    start, end = period_bounds(bundle.equity_curve)

    l2_values = build_level2_values(bundle)
    values.update(l2_values)
    level2 = Level2Snapshot(
        metrics=build_educational_metrics(l2_values),
        diagnosis=build_level2_narrative(l2_values, values),
        values=l2_values,
    )

    l3_values = build_level3_values(
        bundle,
        walkforward,
        payoff_ratio=l2_values.get("payoff_ratio"),
        win_rate=float(values.get("win_rate", 0)),
    )
    values.update(l3_values)

    promotion = promotion_checklist_backtest_paper(values, level3_values=l3_values)

    level1 = Level1Snapshot(
        atlas_score=atlas_score,
        score_label=score_lbl,
        score_emoji=score_emoji,
        confidence=conf_label,
        confidence_emoji=conf_emoji,
        overfitting_risk=of_label,
        overfitting_emoji=of_emoji,
        metrics=[score_metric, conf_metric, *metrics],
        strengths=strengths,
        weaknesses=weaknesses,
        risks=risks,
        summary=summary,
        promotion_backtest_paper=promotion,
    )

    of3_label, of3_emoji = overfitting_risk_l3(l3_values)
    level3 = Level3Snapshot(
        metrics=build_level3_educational_metrics(l3_values),
        diagnosis=build_level3_narrative(l3_values),
        overfitting_risk=of3_label,
        overfitting_emoji=of3_emoji,
        values=l3_values,
        has_walkforward=walkforward is not None,
    )

    return StrategyAnalysis(
        strategy=bundle.strategy,
        source=source,
        market=market,
        timeframe=timeframe,
        period_start=start,
        period_end=end,
        level1=level1,
        level2=level2,
        level3=level3,
        raw=values,
    )


def analyze_path(
    path: str | Path,
    *,
    buy_hold_pct: float | None = None,
    market: str = "BTC/USDT",
    timeframe: str = "4h",
    reports_dir: str | Path | None = None,
) -> StrategyAnalysis:
    path = Path(path)
    bundle = load_report(path)
    reports_dir = Path(reports_dir) if reports_dir else path.parent
    walkforward = load_walkforward(reports_dir, bundle.strategy)
    return analyze_report(
        bundle,
        buy_hold_pct=buy_hold_pct,
        market=market,
        timeframe=timeframe,
        walkforward=walkforward,
    )
