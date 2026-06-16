from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import click

from atlas.core.env import load_project_env
from atlas.core.config import load_config
from atlas.core.models import TradingMode
from atlas.research.backtester import run_backtest
from atlas.research.collector import load_or_download, save_candles_to_db
from atlas.research.statistics import compute_buy_hold_return, compute_statistics, save_report


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@click.group()
def main() -> None:
    """ATLAS QUANT — research, paper, and live trading CLI."""
    load_project_env(PROJECT_ROOT)


@main.group()
def research() -> None:
    """Offline research: data, backtest, reports."""


@research.command("download")
@click.option("--config", "config_path", default="config/backtest.yaml", show_default=True)
@click.option("--force", is_flag=True, help="Re-download even if cache exists")
@click.option("--to-db", is_flag=True, help="Persist candles to PostgreSQL")
def download_data(config_path: str, force: bool, to_db: bool) -> None:
    """Download historical OHLCV from exchange."""
    config = load_config(PROJECT_ROOT / config_path)
    click.echo(f"Downloading {config.exchange.symbol} {config.exchange.timeframe} ({config.data.years}y)...")
    df = load_or_download(config, force=force)
    click.echo(f"Cached {len(df)} candles at {config.data.cache_dir}")
    if to_db:
        count = save_candles_to_db(config, df)
        click.echo(f"Inserted up to {count} rows into PostgreSQL")


@research.command("backtest")
@click.option("--config", "config_path", default="config/backtest.yaml", show_default=True)
@click.option("--output", "output_dir", default="data/reports", show_default=True)
def backtest_cmd(config_path: str, output_dir: str) -> None:
    """Run event-driven backtest with Range Hunter v1."""
    config = load_config(PROJECT_ROOT / config_path)
    df = load_or_download(config)
    if df.empty:
        raise click.ClickException("No data. Run: atlas research download")

    click.echo(f"Running backtest [{config.strategy.name}] on {len(df)} candles...")
    result = run_backtest(config, df)
    report = compute_statistics(result)
    warmup = int(config.strategy.params.get("warmup_bars", 205))
    bh_return = compute_buy_hold_return(df, warmup, config.risk.initial_capital)
    report_name = f"{config.strategy.name}_report"
    path = save_report(result, report, PROJECT_ROOT / output_dir, name=report_name)

    click.echo(f"\n--- Backtest Results ({config.strategy.name}) ---")
    click.echo(f"Net profit:      ${report.net_profit:,.2f} ({report.net_profit_pct:.2%})")
    click.echo(f"Buy & Hold:      {bh_return:.2%}  (same period)")
    click.echo(f"Trades:          {report.total_trades}")
    click.echo(f"Win rate:        {report.win_rate:.2%}")
    click.echo(f"Profit factor:   {report.profit_factor:.2f}")
    click.echo(f"Max drawdown:    {report.max_drawdown_pct:.2%}")
    click.echo(f"Best trade:      {report.best_trade_pct:.2%}")
    click.echo(f"Worst trade:     {report.worst_trade_pct:.2%}")
    if report.sharpe_ratio is not None:
        click.echo(f"Sharpe (approx): {report.sharpe_ratio:.2f}")
    click.echo(f"\nReport saved: {path}")


@research.command("compare")
@click.option("--reports", "reports_dir", default="data/reports", show_default=True)
@click.option("--top", default=10, show_default=True, help="Max strategies to show")
def research_compare(reports_dir: str, top: int) -> None:
    """Rank strategies by Atlas Score (Level 1 intelligence)."""
    from atlas.intelligence.analyzer import analyze_path
    from atlas.intelligence.metrics import discover_reports

    report_paths = discover_reports(PROJECT_ROOT / reports_dir)
    if not report_paths:
        raise click.ClickException(f"No reports in {reports_dir}. Run backtests first.")

    analyses = []
    for path in report_paths:
        try:
            analyses.append(analyze_path(path))
        except Exception as exc:
            click.echo(f"Skip {path.name}: {exc}", err=True)

    analyses.sort(key=lambda a: a.level1.atlas_score, reverse=True)

    click.echo("\n=== ATLAS Intelligence — Ranking ===\n")
    click.echo(
        f"{'#':<3} {'Strategy':<28} {'Score':>6} {'Ret':>8} {'DD':>7} "
        f"{'PF':>5} {'Sharpe':>7} {'Trades':>6} {'Conf':<16}"
    )
    click.echo("-" * 95)

    for i, a in enumerate(analyses[:top], 1):
        raw = a.raw
        sharpe = raw.get("sharpe_ratio")
        sharpe_txt = f"{sharpe:.2f}" if sharpe is not None else "N/A"
        click.echo(
            f"{i:<3} {a.strategy:<28} {a.level1.atlas_score:>6.0f} "
            f"{raw['net_profit_pct']:>7.1%} {raw['max_drawdown_pct']:>6.1%} "
            f"{raw['profit_factor']:>5.2f} {sharpe_txt:>7} "
            f"{int(raw['total_trades']):>6} {a.level1.confidence:<16}"
        )

    best = analyses[0]
    click.echo(f"\nTop: {best.strategy} — Score {best.level1.atlas_score:.0f} ({best.level1.score_label})")
    click.echo(f"Summary: {best.level1.summary}")


@research.command("walkforward")
@click.option("--config", "config_path", default="config/backtest.yaml", show_default=True)
@click.option("--output", "output_dir", default="data/reports", show_default=True)
@click.option("--train-pct", default=0.70, show_default=True, help="In-sample fraction (0–1)")
def research_walkforward(config_path: str, output_dir: str, train_pct: float) -> None:
    """Walk-forward analysis: IS/OOS split + save research JSON."""
    from atlas.intelligence.research_store import save_walkforward
    from atlas.research.walkforward import run_walk_forward

    if not 0.5 <= train_pct <= 0.9:
        raise click.ClickException("train-pct deve estar entre 0.5 e 0.9")

    config = load_config(PROJECT_ROOT / config_path)
    df = load_or_download(config)
    if df.empty:
        raise click.ClickException("No data. Run: atlas research download")

    click.echo(
        f"Walk-forward [{config.strategy.name}] — IS {train_pct:.0%} / OOS {1 - train_pct:.0%} "
        f"({len(df)} candles)..."
    )
    wf = run_walk_forward(config, df, train_pct=train_pct)
    path = save_walkforward(wf, PROJECT_ROOT / output_dir)

    is_s = wf.in_sample
    oos_s = wf.out_of_sample
    wfe_txt = f"{wf.walk_forward_efficiency:.0%}" if wf.walk_forward_efficiency is not None else "N/A"

    click.echo(f"\n--- Walk-Forward ({config.strategy.name}) ---")
    click.echo(f"Split em:        {wf.split_timestamp}")
    click.echo(f"IS retorno:      {is_s.net_profit_pct:.2%} ({wf.is_trades} trades)")
    click.echo(f"OOS retorno:     {oos_s.net_profit_pct:.2%} ({wf.oos_trades} trades)")
    click.echo(f"OOS PF:          {oos_s.profit_factor:.2f}")
    if oos_s.sharpe_ratio is not None:
        click.echo(f"OOS Sharpe:      {oos_s.sharpe_ratio:.2f}")
    click.echo(f"WFE:             {wfe_txt}")
    click.echo(f"\nSalvo: {path}")
    click.echo("Abra o dashboard Intelligence -> Nivel 3 para ver o diagnostico completo.")


@main.group()
def alerts() -> None:
    """Telegram and monitoring alerts."""


@alerts.command("test")
def alerts_test() -> None:
    """Send a test message to Telegram."""
    from atlas.monitoring.alerts import TelegramAlerts

    load_project_env(PROJECT_ROOT)
    tg = TelegramAlerts()
    if not tg.enabled:
        raise click.ClickException(
            "Telegram não configurado. Defina TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env"
        )
    ok = tg.send("✅ ATLAS QUANT — teste de alerta OK")
    if ok:
        click.echo("Mensagem enviada com sucesso.")
    else:
        raise click.ClickException("Falha ao enviar — verifique token e chat_id.")


@main.group()
def trade() -> None:
    """Live operation: paper or real (after promotion gates)."""


@trade.command("check")
@click.option("--config", "config_path", default="config/paper.yaml", show_default=True)
def trade_check(config_path: str) -> None:
    """Test Binance Demo API key, IP whitelist, and permissions."""
    import os
    import urllib.request

    from atlas.brokers.binance import BinanceDemoBroker

    load_project_env(PROJECT_ROOT)
    config = load_config(PROJECT_ROOT / config_path)

    key = os.getenv("BINANCE_DEMO_API_KEY", "").strip()
    secret = os.getenv("BINANCE_DEMO_API_SECRET", "").strip()
    env_file = PROJECT_ROOT / ".env"

    click.echo("=== ATLAS Binance Demo Check ===")
    click.echo(f".env: {'OK' if env_file.is_file() else 'MISSING — copy .env.example to .env'}")
    click.echo(f"API key: {'OK (' + str(len(key)) + ' chars)' if key else 'MISSING'}")
    click.echo(f"Secret:  {'OK (' + str(len(secret)) + ' chars)' if secret else 'MISSING'}")

    if not key or not secret:
        raise click.ClickException("Preencha BINANCE_DEMO_API_KEY e BINANCE_DEMO_API_SECRET no .env")

    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as resp:
            public_ip = resp.read().decode().strip()
        click.echo(f"Seu IP público agora: {public_ip}  ← adicione na whitelist da chave demo")
    except Exception:
        click.echo("Seu IP público: (não foi possível detectar — use https://whatismyipaddress.com)")

    broker = BinanceDemoBroker(config.exchange.symbol)
    diag = broker.check_connection()
    click.echo(f"Demo API: {diag.get('demo_url')}")
    click.echo(f"Candles públicos: {diag.get('ohlcv')}")
    if diag.get("last_close"):
        click.echo(f"BTC último close 4H: {diag.get('last_close')}")
    click.echo(f"Saldo privado:    {diag.get('balance')}")
    if diag.get("usdt_free") is not None:
        click.echo(f"USDT livre:       {diag.get('usdt_free')}")

    if str(diag.get("balance", "")).startswith("fail"):
        click.echo(
            "\nErro -2015 = chave/IP/permissão. Checklist:\n"
            "  1. Chave criada em https://demo.binance.com (NÃO em binance.com)\n"
            "  2. Whitelist: adicione seu IP público na chave\n"
            "  3. Permissões: Leitura + Trading Spot (sem Saques)\n"
            "  4. Se a chave foi criada no site errado, apague e crie outra no DEMO"
        )
        raise click.ClickException("Conexão privada com Binance Demo falhou.")
    click.echo("\nTudo OK — pode rodar: atlas trade paper --once")


@trade.command("paper")
@click.option("--config", "config_path", default="config/paper.yaml", show_default=True)
@click.option("--once", is_flag=True, help="Run single tick instead of 24/7 loop")
def trade_paper(config_path: str, once: bool) -> None:
    """Start paper trading on Binance Demo."""
    from atlas.runtime.runner import TradingRunner

    config = load_config(PROJECT_ROOT / config_path)
    if config.mode != TradingMode.PAPER:
        raise click.ClickException("Config mode must be 'paper'")
    try:
        runner = TradingRunner(config)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    if runner.engine.journal.fallback_message:
        click.echo(f"Warning: {runner.engine.journal.fallback_message}")

    if once:
        try:
            outcome = runner.tick()
        except Exception as exc:
            msg = str(exc)
            if "Invalid API-key" in msg or "-2015" in msg:
                raise click.ClickException(
                    "Binance rejeitou a chave (erro -2015). Verifique:\n"
                    "  1. Chave criada em https://demo.binance.com (não binance.com)\n"
                    "  2. Seu IP público está na whitelist da chave\n"
                    "  3. Permissões: Leitura + Trading Spot (Saques desabilitado)\n"
                    "  4. API Key e Secret corretos no arquivo .env"
                ) from exc
            raise
        click.echo(outcome)
    else:
        click.echo(f"Starting paper trading [{config.strategy.name}] — Ctrl+C to stop")
        runner.run()


@trade.command("live")
@click.option("--config", "config_path", default="config/live.yaml", show_default=True)
@click.confirmation_option(prompt="Real money mode. Continue?")
def trade_live(config_path: str) -> None:
    """Start live trading (requires promotion gates)."""
    from atlas.runtime.runner import TradingRunner

    config = load_config(PROJECT_ROOT / config_path)
    if config.mode != TradingMode.LIVE:
        raise click.ClickException("Config mode must be 'live'")
    try:
        runner = TradingRunner(config)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    if runner.engine.journal.fallback_message:
        click.echo(f"Warning: {runner.engine.journal.fallback_message}")

    runner.run()


@main.command("dashboard")
@click.option("--config", "config_path", default="config/paper.yaml", show_default=True)
@click.option("--port", default=8501, show_default=True)
def dashboard_cmd(config_path: str, port: int) -> None:
    """Launch live trading dashboard (charts, balance, signals, journal)."""
    import subprocess
    import sys

    app_path = Path(__file__).resolve().parent / "dashboard" / "app.py"
    env = os.environ.copy()
    env["ATLAS_CONFIG"] = str(PROJECT_ROOT / config_path)
    click.echo(f"Dashboard ATLAS QUANT → http://localhost:{port}")
    click.echo("Ctrl+C para parar. Rode 'atlas trade paper' em outro terminal para operar.")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.port",
            str(port),
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        check=False,
    )


if __name__ == "__main__":
    main()
