from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from atlas import __version__
from atlas.core.env import get_settings, project_root
from atlas.services.backtest_batch import (
    load_backtest_matrix_from_reports,
    resolve_backtest_config_path,
)
from atlas.services.backtest_jobs import get_active_backtest_job, get_backtest_batch_job, job_snapshot, start_backtest_batch_job
from atlas.runtime.state import bot_state
from atlas.runtime.operational_config import operational_options, save_operational_selection, save_paper_slots, PaperSlot
from atlas.runtime.system_store import save_runtime_system
from atlas.services.operations import get_operations_feed
from atlas.services.terminal import (
    get_dashboard_payload,
    get_intelligence_summary,
    get_journal_entries,
    get_live_payload,
    get_markets_payload,
    get_reports_payload,
    get_results_payload,
    get_risk_payload,
    get_settings_payload,
    get_strategies,
    get_validation_payload,
)
from atlas.runtime.risk_store import update_risk_settings
from atlas.monitoring.alerts import get_alerts


class BacktestRequest(BaseModel):
    config_path: str | None = None
    strategy: str | None = None
    timeframe: str = "4h"
    quote: str = "USDT"
    base_asset: str = "BTC"


class WalkforwardRequest(BaseModel):
    config_path: str | None = None
    strategy: str | None = None
    timeframe: str = "4h"
    quote: str = "USDT"
    base_asset: str = "BTC"
    train_pct: float = 0.70


class OperationalUpdateRequest(BaseModel):
    strategy: str
    timeframe: str = "4h"
    quote: str = "USDT"
    base_asset: str = "BTC"


class PaperSlotRequest(BaseModel):
    strategy: str
    timeframe: str = "4h"
    quote: str = "USDT"
    base: str = "BTC"
    enabled: bool = True


class OperationalSlotsUpdateRequest(BaseModel):
    slots: list[PaperSlotRequest]


class KillSwitchRequest(BaseModel):
    active: bool


class NotificationsUpdateRequest(BaseModel):
    email_daily: bool | None = None
    drawdown_alerts: bool | None = None
    strategy_approval: bool | None = None
    terminal_sounds: bool | None = None


class BacktestAllRequest(BaseModel):
    timeframes: list[str] | None = None
    quote: str = "USDT"
    base_asset: str = "BTC"


class RiskUpdateRequest(BaseModel):
    risk_per_trade_pct: float | None = None
    daily_stop_pct: float | None = None
    daily_target_pct: float | None = None
    max_ops_per_day: int | None = None
    pause_after_losses: int | None = None
    cooldown_minutes: int | None = None


class SystemResetRequest(BaseModel):
    reports: bool = True
    ohlcv_cache: bool = False
    paper_demo: bool = False


class CacheStatusResponse(BaseModel):
    stale: bool = False
    ttl_seconds: float | None = None
    age_seconds: float | None = None
    last_success_at: str | None = None
    error: dict | str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    bot_running: bool
    bot_mode: str
    kill_switch: bool
    binance_demo_configured: bool
    binance_demo_connected: bool
    active_strategy: str | None = None
    active_timeframe: str | None = None
    bot_instances: int = 0


class MarketTickerResponse(BaseModel):
    symbol: str
    price: float
    change_pct: float
    volume_24h: float
    sparkline: list[float] = []


class MarketsResponse(BaseModel):
    items: list[MarketTickerResponse]
    cache: CacheStatusResponse


class MarketChartResponse(BaseModel):
    symbol: str
    base: str
    timeframe: str
    bars: list[dict]
    indicators: list[str] | None = None
    updated_at: str | None = None
    stale: bool = False
    last_success_at: str | None = None
    ttl_seconds: float | None = None
    error: dict | str | None = None


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Quantum-Trend API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        from atlas.brokers.binance import credentials_configured, demo_api_connected

        snap = bot_state.snapshot()
        cfg = operational_options()["active"]
        return HealthResponse(
            status="ok",
            version=__version__,
            bot_running=bool(snap.get("running", False)),
            bot_mode=str(snap.get("mode", "paper")),
            kill_switch=settings.kill_switch_active,
            binance_demo_configured=credentials_configured(live=False),
            binance_demo_connected=demo_api_connected(),
            active_strategy=cfg.get("strategy"),
            active_timeframe=cfg.get("timeframe"),
            bot_instances=int(snap.get("instance_count", 0) or 0),
        )

    @app.get("/api/dashboard")
    def dashboard() -> dict:
        return get_dashboard_payload()

    @app.get("/api/quantum/status")
    def quantum_status() -> dict:
        from atlas.services.quantum_service import get_quantum_status

        return get_quantum_status()

    @app.get("/api/portfolio")
    def portfolio() -> dict:
        from atlas.services.quantum_service import get_portfolio_payload

        return get_portfolio_payload()

    @app.get("/api/platform/status")
    def platform_status() -> dict:
        from atlas.platform.service import get_platform_status

        return get_platform_status()

    @app.get("/api/platform/alerts")
    def platform_alerts() -> dict:
        from atlas.platform.alerts import alert_center_payload

        return alert_center_payload()

    @app.get("/api/platform/decisions")
    def platform_decisions(limit: int = 30) -> dict:
        from atlas.platform.store import load_platform_state

        items = list(load_platform_state().get("decisions") or [])[: max(1, min(limit, 100))]
        return {"items": items, "total": len(items)}

    @app.post("/api/platform/ack-risk")
    def platform_ack_risk() -> dict:
        from atlas.platform.store import acknowledge_risk_lock
        from atlas.platform.state_machine import sync_state_from_runtime
        from atlas.services.terminal import clear_dashboard_cache

        ok = acknowledge_risk_lock()
        if not ok:
            raise HTTPException(status_code=400, detail="Nenhum risk lock ativo para reconhecer.")
        sync_state_from_runtime()
        clear_dashboard_cache()
        return {"ok": True}

    @app.post("/api/platform/stress-test")
    def platform_stress_test() -> dict:
        from atlas.platform.service import run_stress_tests
        from atlas.services.terminal import clear_dashboard_cache

        reports = run_stress_tests()
        clear_dashboard_cache()
        return {"ok": True, "reports": reports}

    @app.get("/api/markets", response_model=MarketsResponse)
    def markets() -> MarketsResponse:
        return MarketsResponse.model_validate(get_markets_payload())

    @app.get("/api/markets/chart", response_model=MarketChartResponse)
    def market_chart(base: str = "BTC", quote: str = "USDT", timeframe: str = "4h") -> MarketChartResponse:
        from atlas.services.market_chart import get_market_chart_payload

        return MarketChartResponse.model_validate(
            get_market_chart_payload(base=base, quote=quote, timeframe=timeframe)
        )

    @app.get("/api/backtests/chart")
    def backtest_chart(
        strategy: str,
        timeframe: str,
        base_asset: str = "BTC",
        quote: str = "USDT",
    ) -> dict:
        from atlas.services.backtest_chart import get_backtest_chart_payload

        return get_backtest_chart_payload(
            strategy=strategy,
            timeframe=timeframe,
            base=base_asset,
            quote=quote,
        )

    @app.get("/api/positions")
    def positions() -> dict:
        from atlas.runtime.state import build_positions

        return {"items": [p.model_dump() for p in build_positions()]}

    @app.get("/api/strategies")
    def strategies() -> dict:
        return {"items": [s.model_dump() for s in get_strategies()]}

    @app.get("/api/journal")
    def journal() -> dict:
        return {"items": get_journal_entries()}

    @app.get("/api/intelligence")
    async def intelligence() -> dict:
        return await asyncio.to_thread(get_intelligence_summary)

    @app.get("/api/intelligence/analysis")
    def intelligence_analysis(strategy: str | None = None) -> dict:
        from atlas.services.intelligence_service import get_strategy_analysis

        analysis = get_strategy_analysis(strategy)
        if not analysis:
            raise HTTPException(status_code=404, detail="Nenhum relatório de backtest encontrado")
        return analysis

    @app.get("/api/bot/status")
    def bot_status() -> dict:
        return bot_state.snapshot()

    @app.post("/api/bot/start")
    def bot_start() -> dict:
        from atlas.services.terminal import clear_dashboard_cache

        try:
            bot_state.start_paper()
        except RuntimeError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        from atlas.platform.state_machine import sync_state_from_runtime

        sync_state_from_runtime()
        clear_dashboard_cache()
        return bot_state.snapshot()

    @app.post("/api/bot/start-live")
    def bot_start_live() -> dict:
        from atlas.services.terminal import clear_dashboard_cache

        try:
            bot_state.start_live()
        except RuntimeError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        from atlas.platform.state_machine import sync_state_from_runtime

        sync_state_from_runtime()
        clear_dashboard_cache()
        return bot_state.snapshot()

    @app.get("/api/operations/feed")
    def operations_feed(limit: int = 100) -> dict:
        return get_operations_feed(limit=min(max(limit, 10), 200))

    @app.get("/api/operations/stream")
    async def operations_stream() -> StreamingResponse:
        async def event_generator():
            while True:
                payload = get_operations_feed(limit=100)
                yield f"data: {json.dumps(payload, default=str)}\n\n"
                await asyncio.sleep(3)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/live")
    def live_view() -> dict:
        return get_live_payload()

    @app.get("/api/live/gates")
    def live_gates() -> dict:
        from atlas.runtime.live_gates import evaluate_live_gates

        return evaluate_live_gates()

    @app.post("/api/bot/stop")
    def bot_stop() -> dict:
        from atlas.services.terminal import clear_dashboard_cache

        bot_state.stop()
        from atlas.platform.state_machine import sync_state_from_runtime

        sync_state_from_runtime()
        clear_dashboard_cache()
        return bot_state.snapshot()

    def _resolve_backtest_config(body: BacktestRequest | WalkforwardRequest) -> tuple[str, str, str]:
        strategy = body.strategy or "mm200_trend_v2"
        tf = body.timeframe.lower()
        quote = body.quote.upper()
        config_rel = resolve_backtest_config_path(strategy, tf, config_path=body.config_path)
        return config_rel, tf, quote

    @app.post("/api/backtest/all")
    async def backtest_all(body: BacktestAllRequest | None = None) -> dict:
        opts = body or BacktestAllRequest()
        timeframes = tuple(t.lower() for t in (opts.timeframes or ["1h", "4h", "1d"]))
        try:
            job_id = await asyncio.to_thread(
                start_backtest_batch_job,
                timeframes=timeframes,
                quote=opts.quote.upper(),
                base_asset=opts.base_asset.upper(),
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        job = get_backtest_batch_job(job_id)
        return job_snapshot(job) if job else {"job_id": job_id, "status": "running", "total": 0, "completed": 0}

    @app.get("/api/backtest/all/active")
    def backtest_all_active() -> dict:
        job = get_active_backtest_job()
        if job is None:
            return {"active": False}
        return {"active": True, **job_snapshot(job)}

    @app.get("/api/backtest/all/{job_id}")
    def backtest_all_status(job_id: str) -> dict:
        job = get_backtest_batch_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job não encontrado — reinicie a matriz.")
        return job_snapshot(job)

    @app.get("/api/backtest/matrix")
    def backtest_matrix(quote: str = "USDT") -> dict:
        return load_backtest_matrix_from_reports(quote=quote.upper())

    @app.post("/api/backtest")
    def backtest(body: BacktestRequest) -> dict:
        from atlas.dashboard.actions import run_backtest_dashboard
        from atlas.services.terminal import clear_dashboard_cache, clear_intelligence_cache

        config_rel, tf, quote = _resolve_backtest_config(body)
        result = run_backtest_dashboard(
            project_root(),
            config_rel,
            timeframe=tf,
            quote=quote,
            base_asset=body.base_asset,
        )
        if not result.get("ok", True):
            raise HTTPException(status_code=400, detail=result.get("error", "Backtest falhou"))
        clear_dashboard_cache()
        clear_intelligence_cache()
        metrics = {
            "total_return_pct": round(float(result.get("net_profit_pct", 0)) * 100, 2),
            "profit_factor": float(result.get("profit_factor", 0)),
            "max_drawdown_pct": round(float(result.get("max_drawdown_pct", 0)) * 100, 2),
            "sharpe": float(result.get("sharpe_ratio", 0) or 0),
            "win_rate_pct": round(float(result.get("win_rate", 0)) * 100, 2),
            "trades": int(result.get("total_trades", 0)),
            "expectancy": 0.0,
            "atlas_score": 0.0,
        }
        return {
            "metrics": metrics,
            "report_path": result.get("report_path", ""),
            "strategy": result.get("strategy", body.strategy),
            "timeframe": result.get("timeframe", tf),
        }

    @app.post("/api/research/walkforward")
    def walkforward(body: WalkforwardRequest) -> dict:
        from atlas.research.backtester import run_walkforward_from_yaml
        from atlas.services.terminal import clear_intelligence_cache

        config_rel, _, _ = _resolve_backtest_config(body)
        path = run_walkforward_from_yaml(config_rel, train_pct=body.train_pct)
        clear_intelligence_cache()
        return {"ok": True, "report_path": str(path)}

    @app.get("/api/validation")
    def validation() -> dict:
        return get_validation_payload()

    @app.get("/api/risk")
    def risk() -> dict:
        return get_risk_payload()

    @app.put("/api/risk")
    def risk_update(body: RiskUpdateRequest) -> dict:
        from atlas.services.terminal import clear_dashboard_cache, clear_risk_cache

        update_risk_settings(**body.model_dump(exclude_none=True))
        clear_dashboard_cache()
        clear_risk_cache()
        return get_risk_payload()

    @app.get("/api/results")
    def results(strategy: str | None = None, timeframe: str | None = None, base_asset: str = "BTC") -> dict:
        return get_results_payload(strategy=strategy, timeframe=timeframe, base_asset=base_asset)

    @app.get("/api/results/{strategy}/{timeframe}")
    def results_by_path(strategy: str, timeframe: str, base_asset: str = "BTC") -> dict:
        try:
            return get_results_payload(strategy=strategy, timeframe=timeframe, base_asset=base_asset)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/reports")
    def reports() -> dict:
        return get_reports_payload()

    @app.get("/api/settings")
    def settings_view() -> dict:
        return get_settings_payload()

    @app.get("/api/system/options")
    def system_options() -> dict:
        return operational_options()

    @app.put("/api/settings/operational")
    def settings_operational(body: OperationalUpdateRequest) -> dict:
        from atlas.services.terminal import clear_dashboard_cache, clear_intelligence_cache

        if bot_state.running:
            raise HTTPException(status_code=409, detail="Pare o bot antes de trocar estratégia/timeframe")
        try:
            save_operational_selection(
                strategy_name=body.strategy,
                timeframe=body.timeframe,
                quote_asset=body.quote,
                base_asset=body.base_asset,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        clear_dashboard_cache()
        clear_intelligence_cache()
        return get_settings_payload()

    @app.put("/api/settings/operational/slots")
    def settings_operational_slots(body: OperationalSlotsUpdateRequest) -> dict:
        from atlas.runtime.operational_config import MAX_PAPER_SLOTS, PaperSlot, save_paper_slots
        from atlas.services.terminal import clear_dashboard_cache, clear_intelligence_cache

        if bot_state.running:
            raise HTTPException(status_code=409, detail="Pare o bot antes de alterar slots")
        try:
            slots = [
                PaperSlot(
                    strategy=s.strategy,
                    timeframe=s.timeframe,
                    quote=s.quote,
                    base=s.base,
                    enabled=s.enabled,
                )
                for s in body.slots[:MAX_PAPER_SLOTS]
            ]
            save_paper_slots(slots)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        clear_dashboard_cache()
        clear_intelligence_cache()
        return get_settings_payload()

    @app.put("/api/settings/kill-switch")
    def settings_kill_switch(body: KillSwitchRequest) -> dict:
        save_runtime_system(kill_switch=body.active)
        return get_settings_payload()

    @app.put("/api/settings/notifications")
    def settings_notifications(body: NotificationsUpdateRequest) -> dict:
        save_runtime_system(notifications=body.model_dump(exclude_none=True))
        return get_settings_payload()

    @app.post("/api/alerts/test")
    def alerts_test() -> dict:
        alerts = get_alerts()
        if not alerts.configured:
            raise HTTPException(
                status_code=400,
                detail="Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env",
            )
        ok = alerts.notify_test()
        if not ok:
            raise HTTPException(status_code=502, detail="Falha ao enviar mensagem Telegram")
        return {"ok": True, "configured": True}

    @app.post("/api/system/reset")
    def system_reset(body: SystemResetRequest) -> dict:
        from atlas.services.system_reset import ResetOptions, reset_system_data

        if not body.reports and not body.ohlcv_cache and not body.paper_demo:
            raise HTTPException(status_code=400, detail="Selecione ao menos uma opção para resetar.")

        if body.paper_demo and bot_state.running:
            raise HTTPException(
                status_code=409,
                detail="Pare o bot antes de resetar dados do paper trading.",
            )

        result = reset_system_data(
            ResetOptions(
                reports=body.reports,
                ohlcv_cache=body.ohlcv_cache,
                paper_demo=body.paper_demo,
            )
        )
        from atlas.services.terminal import clear_dashboard_cache, clear_intelligence_cache

        clear_dashboard_cache()
        clear_intelligence_cache()
        try:
            from atlas.services.backtest_jobs import clear_backtest_job_cache

            clear_backtest_job_cache()
        except ImportError:
            pass
        from atlas.core.env import project_root

        return {
            "ok": True,
            "deleted_files": result.deleted_files,
            "cleared_files": result.cleared_files,
            "risk_counters_reset": result.risk_counters_reset,
            "quantum_state_cleared": result.quantum_state_cleared,
            "deleted_count": len(result.deleted_files),
            "cleared_count": len(result.cleared_files),
            "reports_dir": str(project_root() / "data" / "reports"),
        }

    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "atlas.api.main:app",
        host=settings.atlas_api_host,
        port=settings.atlas_api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
