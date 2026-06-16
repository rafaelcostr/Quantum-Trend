"""Config operacional compartilhada entre paginas do dashboard."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from atlas.core.config import AtlasConfig, load_config
from atlas.dashboard.strategy_config import build_operational_config, load_active_config


def get_ops_config(project_root: Path, paper_config_rel: str = "config/paper.yaml") -> AtlasConfig:
    """Retorna config ativa da sessao, arquivo salvo ou paper.yaml."""
    cached = st.session_state.get("atlas_ops_config")
    if isinstance(cached, AtlasConfig):
        return cached

    active = load_active_config(project_root, paper_config_rel)
    st.session_state["atlas_ops_config"] = active
    return active


def set_ops_config(config: AtlasConfig) -> None:
    st.session_state["atlas_ops_config"] = config


def build_ops_from_session(
    project_root: Path,
    paper_config_rel: str = "config/paper.yaml",
) -> AtlasConfig:
    """Reconstrói config a partir dos selects da sidebar."""
    base = load_config(project_root / paper_config_rel)
    strategy = st.session_state.get("atlas_strategy", base.strategy.name)
    quote = st.session_state.get("atlas_quote", "USDT")
    timeframe = st.session_state.get("atlas_timeframe", base.exchange.timeframe)
    return build_operational_config(
        project_root,
        strategy_name=strategy,
        quote_asset=quote,
        timeframe=timeframe,
        base_config_rel=paper_config_rel,
    )
