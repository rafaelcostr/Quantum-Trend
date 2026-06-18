from __future__ import annotations

import click

from atlas.research.backtester import run_backtest_from_yaml, run_walkforward_from_yaml
from atlas.services.backtest_batch import run_all_strategies_backtest


@click.group()
def main() -> None:
    """Quantum-Trend CLI."""


@main.command("backtest")
@click.option("--config", "config_path", default="config/backtest_mm200_v2.yaml", show_default=True)
def backtest_cmd(config_path: str) -> None:
    metrics, path = run_backtest_from_yaml(config_path)
    click.echo(f"Atlas Score: {metrics.atlas_score}")
    click.echo(f"PF: {metrics.profit_factor} | DD: {metrics.max_drawdown_pct}% | Trades: {metrics.trades}")
    click.echo(f"Relatório: {path}")


@main.command("backtest-all")
@click.option("--quote", default="USDT", show_default=True)
def backtest_all_cmd(quote: str) -> None:
    """Roda backtest de todas as estratégias em 1H, 4H e 1D."""
    summary = run_all_strategies_backtest(quote=quote)
    click.echo(f"Concluídos: {summary['completed']}/{summary['total_runs']} | Falhas: {summary['failed']}")
    if summary.get("best"):
        b = summary["best"]
        click.echo(
            f"Melhor: {b['strategy_label']} · {b['timeframe'].upper()} · "
            f"Score {b.get('metrics', {}).get('atlas_score', 0)}"
        )
    for item in summary["items"]:
        if not item.get("ok"):
            click.echo(f"ERRO {item['strategy']} {item['timeframe']}: {item.get('error')}", err=True)
            continue
        m = item.get("metrics", {})
        click.echo(
            f"{item['strategy_label']:28} {item['timeframe'].upper():3} "
            f"Score {m.get('atlas_score', 0):5} PF {m.get('profit_factor', 0):4} "
            f"Trades {m.get('trades', 0):4}"
        )


@main.group("research")
def research_group() -> None:
    """Pesquisa quantitativa (walk-forward, etc.)."""


@research_group.command("walkforward")
@click.option("--config", "config_path", default="config/backtest_mm200_v2.yaml", show_default=True)
@click.option("--train-pct", default=0.70, show_default=True, type=float)
def walkforward_cmd(config_path: str, train_pct: float) -> None:
    path = run_walkforward_from_yaml(config_path, train_pct=train_pct)
    click.echo(f"Walk-forward salvo: {path}")


@main.command("api")
def api_cmd() -> None:
    from atlas.api.main import run

    run()


@main.group("alerts")
def alerts_group() -> None:
    """Alertas Telegram."""


@alerts_group.command("test")
def alerts_test_cmd() -> None:
    """Envia mensagem de teste no Telegram."""
    from atlas.monitoring.alerts import get_alerts

    alerts = get_alerts()
    if not alerts.configured:
        raise click.ClickException("Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env")
    if alerts.notify_test():
        click.echo("Mensagem de teste enviada.")
    else:
        raise click.ClickException("Falha ao enviar mensagem Telegram")


if __name__ == "__main__":
    main()
