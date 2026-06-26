from __future__ import annotations

import pytest

from atlas.runtime.operational_config import (
    PaperSlot,
    load_paper_slots,
    save_operational_selection,
    save_paper_slots,
    slot_key,
    _normalize_paper_slots,
)


def test_slot_key():
    assert slot_key("mm200_trend_v2", "4h") == "mm200_trend_v2_4h_btc"
    assert slot_key("mm200_trend_v2", "1d", "ETH") == "mm200_trend_v2_1d_eth"


def test_save_paper_slots_allows_4h_and_1d_same_strategy():
    slots = [
        PaperSlot(strategy="mm200_trend_v2", timeframe="4h", enabled=True),
        PaperSlot(strategy="mm200_trend_v2", timeframe="1d", enabled=True),
        PaperSlot(strategy="range_hunter_v1", timeframe="4h", enabled=False),
    ]
    saved = save_paper_slots(slots)
    assert len(saved) == 12
    assert saved[0].timeframe == "4h"
    assert saved[1].timeframe == "1d"


def test_save_paper_slots_rejects_duplicate_combo():
    slots = [
        PaperSlot(strategy="mm200_trend_v2", timeframe="4h", enabled=True),
        PaperSlot(strategy="mm200_trend_v2", timeframe="4h", enabled=True),
    ]
    with pytest.raises(ValueError, match="duplicada"):
        save_paper_slots(slots)


def test_save_paper_slots_truncates_more_than_six_per_base():
    slots = [
        PaperSlot(strategy="pullback_ema20_v1", timeframe="4h", base="BTC", enabled=True),
        PaperSlot(strategy="mm200_trend_v2", timeframe="1h", base="BTC", enabled=True),
        PaperSlot(strategy="range_hunter_v1", timeframe="4h", base="BTC", enabled=True),
        PaperSlot(strategy="bb_squeeze_v1", timeframe="1d", base="BTC", enabled=True),
        PaperSlot(strategy="breakout_high20_v1", timeframe="1h", base="BTC", enabled=True),
        PaperSlot(strategy="supertrend_mm200_v1", timeframe="4h", base="BTC", enabled=True),
        PaperSlot(strategy="mm200_daily_macro_v1", timeframe="1d", base="BTC", enabled=True),
    ]
    saved = save_paper_slots(slots)
    btc = [s for s in saved if s.base == "BTC"]
    assert len(btc) == 6
    assert not any(s.strategy == "mm200_daily_macro_v1" for s in btc)


def test_save_paper_slots_allows_six_btc_and_six_eth():
    slots = [
        PaperSlot(strategy="pullback_ema20_v1", timeframe="4h", base="BTC", enabled=True),
        PaperSlot(strategy="mm200_trend_v2", timeframe="1d", base="BTC", enabled=True),
        PaperSlot(strategy="range_hunter_v1", timeframe="4h", base="ETH", enabled=True),
        PaperSlot(strategy="pullback_ema20_v1", timeframe="1h", base="ETH", enabled=True),
    ]
    saved = save_paper_slots(slots)
    assert len(saved) == 12
    eth_enabled = [s for s in saved if s.base == "ETH" and s.enabled]
    assert len(eth_enabled) == 2


def test_normalize_paper_slots_orders_btc_then_eth():
    slots = [
        PaperSlot(strategy="range_hunter_v1", timeframe="4h", base="ETH", enabled=True),
        PaperSlot(strategy="pullback_ema20_v1", timeframe="4h", base="BTC", enabled=True),
    ]
    norm = _normalize_paper_slots(slots)
    assert len(norm) == 12
    assert all(s.base == "BTC" for s in norm[:6])
    assert all(s.base == "ETH" for s in norm[6:])
    assert norm[0].strategy == "pullback_ema20_v1"
    assert norm[6].strategy == "range_hunter_v1"


def test_normalize_paper_slots_uses_positional_layout_when_twelve_rows():
    slots = [
        PaperSlot(strategy="pullback_ema20_v1", timeframe="4h", base="BTC", enabled=True),
    ]
    slots.extend(PaperSlot(strategy="pullback_ema20_v1", timeframe="4h", base="BTC", enabled=False) for _ in range(5))
    slots.extend(
        PaperSlot(strategy="breakout_high20_v1", timeframe="1h", base="BTC", enabled=True) for _ in range(6)
    )
    norm = _normalize_paper_slots(slots)
    assert norm[6].base == "ETH"
    assert norm[6].strategy == "breakout_high20_v1"
    assert norm[6].enabled is True


def test_save_operational_selection_keeps_eth_slots(tmp_path, monkeypatch):
    from atlas.runtime import operational_config as oc

    slots_path = tmp_path / "paper_slots.yaml"
    monkeypatch.setattr(oc, "_slots_path", lambda: slots_path)

    initial = _normalize_paper_slots(
        [
            PaperSlot(strategy="pullback_ema20_v1", timeframe="4h", base="BTC", enabled=True),
            PaperSlot(strategy="supertrend_mm200_v1", timeframe="1h", base="ETH", enabled=True),
        ]
    )
    save_paper_slots(initial)

    save_operational_selection(
        strategy_name="breakout_high20_v1",
        timeframe="4h",
        base_asset="BTC",
    )
    loaded = load_paper_slots()
    eth = [s for s in loaded if s.base == "ETH" and s.enabled]
    assert any(s.strategy == "supertrend_mm200_v1" for s in eth)
    assert loaded[0].strategy == "breakout_high20_v1"
    assert loaded[0].base == "BTC"
