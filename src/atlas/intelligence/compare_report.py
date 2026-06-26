"""Relatório comparativo — todos os backtests em um único Markdown."""
from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atlas.intelligence.analyzer import analyze_path
from atlas.intelligence.metrics import discover_reports
from atlas.intelligence.models import StrategyAnalysis
from atlas.intelligence.report import render_ai_report


def _pct(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val:.2%}"


def _row_label(analysis: StrategyAnalysis) -> str:
    meta = analysis.metadata
    tf = str(meta.get("timeframe") or analysis.timeframe).upper()
    market = meta.get("market") or analysis.market
    stype = meta.get("strategy_type") or ""
    base = f"{analysis.strategy} · {market} · {tf}"
    if stype:
        return f"{base} ({stype})"
    return base


def render_comparison_summary(analyses: list[StrategyAnalysis], errors: list[tuple[str, str]]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        "# ATLAS QUANT — RELATÓRIO COMPARATIVO",
        "",
        f"**Gerado em:** {now} ",
        f"**Total analisado:** {len(analyses)} backtest(s) ",
        "",
        "---",
        "",
        "## Ranking por Atlas Score",
        "",
        "| # | Estratégia | Par | TF | Tipo | Score | Classif. | Retorno | DD | PF | Sharpe | Trades | Confiança |",
        "|---|------------|-----|----|------|-------|----------|---------|----|----|--------|--------|-----------|",
    ]

    for i, a in enumerate(analyses, 1):
        meta = a.metadata
        raw = a.raw
        l1 = a.level1
        sharpe = raw.get("sharpe_ratio")
        sharpe_txt = f"{sharpe:.2f}" if sharpe is not None else "N/A"
        lines.append(
            f"| {i} "
            f"| {a.strategy} "
            f"| {meta.get('market', a.market)} "
            f"| {str(meta.get('timeframe') or a.timeframe).upper()} "
            f"| {meta.get('strategy_type', 'N/A')} "
            f"| {l1.atlas_score:.0f} "
            f"| {l1.score_label} "
            f"| {_pct(raw.get('net_profit_pct'))} "
            f"| {_pct(raw.get('max_drawdown_pct'))} "
            f"| {raw.get('profit_factor', 0):.2f} "
            f"| {sharpe_txt} "
            f"| {int(raw.get('total_trades', 0))} "
            f"| {l1.confidence} |"
        )

    if errors:
        lines.extend(["", "## Relatórios ignorados (erro)", ""])
        for name, err in errors:
            lines.append(f"- `{name}` — {err}")

    if analyses:
        best = analyses[0]
        lines.extend(
            [
                "",
                "---",
                "",
                "## Resumo executivo",
                "",
                f"**Melhor Atlas Score:** {_row_label(best)} — "
                f"**{best.level1.atlas_score:.0f}/100** ({best.level1.score_label})",
                "",
                f"**Retorno:** {_pct(best.raw.get('net_profit_pct'))} · "
                f"**PF:** {best.raw.get('profit_factor', 0):.2f} · "
                f"**DD:** {_pct(best.raw.get('max_drawdown_pct'))}",
                "",
                "### Destaques rápidos",
                "",
            ]
        )
        for a in analyses[:5]:
            l1 = a.level1
            summary = l1.summary
            if len(summary) > 120:
                summary = summary[:120] + "..."
            lines.append(
                f"- **{_row_label(a)}** — Score {l1.atlas_score:.0f} · "
                f"Retorno {_pct(a.raw.get('net_profit_pct'))} · {summary}"
            )

        promoted = [a for a in analyses if a.level1.atlas_score >= 70]
        rejected = [a for a in analyses if a.level1.atlas_score < 60]
        if promoted:
            lines.append("")
            lines.append(f"**Promissoras (score ≥ 70):** {len(promoted)}")
        if rejected:
            lines.append(f"**Rejeitadas (score < 60):** {len(rejected)}")

    lines.extend(["", "---", "", "## Ficha por backtest", ""])
    for a in analyses:
        meta = a.metadata
        l1 = a.level1
        raw = a.raw
        fname = Path(str(meta.get("source_path") or "")).name or meta.get("report_name", "N/A")
        lines.extend(
            [
                f"### {_row_label(a)}",
                "",
                f"- **Arquivo:** `{fname}`",
                f"- **Config:** `{meta.get('config_file', 'N/A')}`",
                f"- **Período:** {a.period_start or '?'} → {a.period_end or '?'}",
                f"- **Atlas Score:** {l1.atlas_score:.0f}/100 — {l1.score_emoji} {l1.score_label}",
                f"- **Retorno:** {_pct(raw.get('net_profit_pct'))} · "
                f"**PF:** {raw.get('profit_factor', 0):.2f} · "
                f"**DD:** {_pct(raw.get('max_drawdown_pct'))} · "
                f"**Trades:** {int(raw.get('total_trades', 0))}",
                f"- **Resumo:** {l1.summary}",
                "",
            ]
        )

    return "\n".join(lines)


def render_full_consolidated_report(
    analyses: list[StrategyAnalysis],
    errors: list[tuple[str, str]],
) -> str:
    """Comparação + cada relatório ATLAS Intelligence completo."""
    parts = [render_comparison_summary(analyses, errors)]
    if analyses:
        parts.append("\n---\n\n# RELATÓRIOS INDIVIDUAIS COMPLETOS\n")
        for a in analyses:
            parts.append(f"\n---\n\n{render_ai_report(a)}\n")
    return "\n".join(parts)


UNIFIED_AI_REPORT_NAME = "atlas_relatorio_unico_todas_estrategias.md"


def render_unified_ai_report(
    analyses: list[StrategyAnalysis],
    errors: list[tuple[str, str]],
) -> str:
    """Um único Markdown com todas as estratégias — pronto para colar em uma IA."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    preamble = f"""# ATLAS QUANT — RELATÓRIO ÚNICO · TODAS AS ESTRATÉGIAS

**Gerado em:** {now} 
**Backtests incluídos:** {len(analyses)}

## Como usar com IA

Cole **este documento inteiro** em ChatGPT, Claude, Gemini ou similar e peça, por exemplo:

1. Comparar todas as estratégias (retorno, drawdown, profit factor, Sharpe, Atlas Score)
2. Dizer quais merecem paper trading e quais rejeitar
3. Explicar trade-offs (mean reversion vs trend, 4h vs 1d, USDT vs USDC)
4. Apontar overfitting, poucos trades ou risco oculto
5. Sugerir próximos passos de pesquisa e otimização

---

"""
    return preamble + render_full_consolidated_report(analyses, errors)


def analyze_all_reports(reports_dir: Path) -> tuple[list[StrategyAnalysis], list[tuple[str, str]]]:
    analyses: list[StrategyAnalysis] = []
    errors: list[tuple[str, str]] = []
    for path in discover_reports(reports_dir):
        try:
            analyses.append(analyze_path(path))
        except Exception as exc:
            errors.append((path.name, str(exc)))
    analyses.sort(key=lambda a: a.level1.atlas_score, reverse=True)
    return analyses, errors


def build_comparison_report(
    reports_dir: Path,
    *,
    include_full: bool = True,
) -> dict[str, Any]:
    analyses, errors = analyze_all_reports(reports_dir)
    if not analyses and not errors:
        return {"ok": False, "error": "Nenhum relatório em data/reports/. Rode backtests em Pesquisa."}

    if include_full:
        markdown = render_full_consolidated_report(analyses, errors)
    else:
        markdown = render_comparison_summary(analyses, errors)

    return {
        "ok": True,
        "markdown": markdown,
        "count": len(analyses),
        "errors": errors,
    }


def _export_filename(analysis: StrategyAnalysis) -> str:
    meta = analysis.metadata
    tf = str(meta.get("timeframe") or analysis.timeframe).lower()
    quote = str(meta.get("quote") or "usdt").lower()
    return f"atlas_{analysis.strategy}_{tf}_{quote}.md"


def export_all_reports(
    reports_dir: Path,
    *,
    include_full_consolidated: bool = True,
) -> dict[str, Any]:
    """Gera comparativo + um .md por backtest + ZIP com tudo."""
    export_dir = reports_dir / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    analyses, errors = analyze_all_reports(reports_dir)
    if not analyses and not errors:
        return {"ok": False, "error": "Nenhum relatório em data/reports/. Rode backtests em Pesquisa."}

    summary_md = render_comparison_summary(analyses, errors)
    summary_path = reports_dir / "atlas_comparativo_resumo.md"
    summary_path.write_text(summary_md, encoding="utf-8")

    unified_md = render_unified_ai_report(analyses, errors)
    unified_path = reports_dir / UNIFIED_AI_REPORT_NAME
    unified_path.write_text(unified_md, encoding="utf-8")

    full_path: Path | None = unified_path

    individual_paths: list[Path] = []
    individual_files: list[dict[str, Any]] = []
    for analysis in analyses:
        out = export_dir / _export_filename(analysis)
        out.write_text(render_ai_report(analysis), encoding="utf-8")
        individual_paths.append(out)
        individual_files.append(
            {
                "path": str(out),
                "file_name": out.name,
                "label": _row_label(analysis),
                "score": analysis.level1.atlas_score,
            }
        )

    zip_path = reports_dir / "atlas_todos_relatorios.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(unified_path, arcname=unified_path.name)
        zf.write(summary_path, arcname=summary_path.name)
        for path in individual_paths:
            zf.write(path, arcname=f"individual/{path.name}")

    return {
        "ok": True,
        "count": len(analyses),
        "individual_count": len(individual_paths),
        "errors": errors,
        "summary_path": str(summary_path),
        "unified_path": str(unified_path),
        "full_path": str(unified_path),
        "export_dir": str(export_dir),
        "zip_path": str(zip_path),
        "individual_files": individual_files,
    }
