from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from atlas.core.config import default_paper_config
from atlas.core.env import project_root
from atlas.core.models import RiskConfig


@dataclass
class RuntimeRiskSettings:
    risk_per_trade_pct: float = 1.0
    daily_stop_pct: float = 3.0
    daily_target_pct: float = 5.0
    max_ops_per_day: int = 20
    pause_after_losses: int = 3
    cooldown_minutes: int = 60
    consecutive_losses: int = 0
    paused_until: str | None = None
    trades_today: int = 0
    daily_pnl: float = 0.0

    @classmethod
    def from_config(cls, risk: RiskConfig) -> RuntimeRiskSettings:
        return cls(
            risk_per_trade_pct=risk.risk_per_trade * 100,
            daily_stop_pct=risk.max_daily_drawdown * 100,
        )

    def to_dict(self) -> dict:
        return {
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "daily_stop_pct": self.daily_stop_pct,
            "daily_target_pct": self.daily_target_pct,
            "max_ops_per_day": self.max_ops_per_day,
            "pause_after_losses": self.pause_after_losses,
            "cooldown_minutes": self.cooldown_minutes,
            "consecutive_losses": self.consecutive_losses,
            "paused_until": self.paused_until,
            "trades_today": self.trades_today,
            "daily_pnl": round(self.daily_pnl, 2),
        }


_PATH = project_root() / "data" / "runtime" / "risk.json"
_store: RuntimeRiskSettings | None = None


def get_risk_settings() -> RuntimeRiskSettings:
    global _store
    if _store is not None:
        return _store
    cfg = default_paper_config()
    _store = RuntimeRiskSettings.from_config(cfg.risk)
    if _PATH.exists():
        raw = json.loads(_PATH.read_text(encoding="utf-8"))
        for key, val in raw.items():
            if hasattr(_store, key):
                setattr(_store, key, val)
    return _store


def update_risk_settings(**kwargs: float | int) -> RuntimeRiskSettings:
    store = get_risk_settings()
    for key, val in kwargs.items():
        if hasattr(store, key) and val is not None:
            setattr(store, key, val)
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(store.to_dict(), indent=2), encoding="utf-8")
    from atlas.runtime.bot_runner import bot_pool

    for _key, engine in bot_pool.engines():
        apply_risk_to_engine(engine)
    return store


def apply_risk_to_engine(engine) -> None:
    """Sincroniza limites da UI com o RiskManager em execução."""
    store = get_risk_settings()
    cfg = engine.risk.config
    cfg.risk_per_trade = store.risk_per_trade_pct / 100.0
    cfg.max_daily_drawdown = store.daily_stop_pct / 100.0
    cfg.max_weekly_drawdown = max(cfg.max_daily_drawdown * 2, store.daily_stop_pct / 100.0 * 1.5)
    cfg.max_open_positions = min(cfg.max_open_positions, 5)


def is_trading_paused() -> tuple[bool, str]:
    store = get_risk_settings()
    if store.paused_until:
        try:
            until = datetime.fromisoformat(str(store.paused_until).replace("Z", "+00:00"))
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) < until:
                return True, f"cooldown ativo até {until.strftime('%H:%M UTC')}"
        except ValueError:
            pass
    if store.consecutive_losses >= store.pause_after_losses:
        return True, f"{store.consecutive_losses} perdas consecutivas — pausa operacional"
    if store.trades_today >= store.max_ops_per_day:
        return True, "limite diário de operações atingido"
    return False, ""


def record_trade_open() -> None:
    store = get_risk_settings()
    store.trades_today += 1
    _persist(store)


def record_trade_close(*, pnl: float) -> None:
    store = get_risk_settings()
    store.daily_pnl = round(store.daily_pnl + pnl, 2)
    if pnl < 0:
        store.consecutive_losses += 1
        if store.consecutive_losses >= store.pause_after_losses:
            until = datetime.now(timezone.utc) + timedelta(minutes=store.cooldown_minutes)
            store.paused_until = until.isoformat()
    else:
        store.consecutive_losses = 0
    _persist(store)


def _persist(store: RuntimeRiskSettings) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(store.to_dict(), indent=2), encoding="utf-8")


def reset_risk_counters() -> RuntimeRiskSettings:
    """Zera contadores diários e cooldown — mantém limites configurados."""
    store = get_risk_settings()
    store.consecutive_losses = 0
    store.paused_until = None
    store.trades_today = 0
    store.daily_pnl = 0.0
    _persist(store)
    return store
