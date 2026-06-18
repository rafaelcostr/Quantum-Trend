from __future__ import annotations

import pytest

from atlas.runtime.operational_config import PaperSlot, save_paper_slots, slot_key


def test_slot_key():
    assert slot_key("mm200_trend_v2", "4h") == "mm200_trend_v2_4h"
    assert slot_key("mm200_trend_v2", "1d") == "mm200_trend_v2_1d"


def test_save_paper_slots_allows_4h_and_1d_same_strategy():
    slots = [
        PaperSlot(strategy="mm200_trend_v2", timeframe="4h", enabled=True),
        PaperSlot(strategy="mm200_trend_v2", timeframe="1d", enabled=True),
        PaperSlot(strategy="range_hunter_v1", timeframe="4h", enabled=False),
    ]
    saved = save_paper_slots(slots)
    assert len(saved) == 3
    assert saved[0].timeframe == "4h"
    assert saved[1].timeframe == "1d"


def test_save_paper_slots_rejects_duplicate_combo():
    slots = [
        PaperSlot(strategy="mm200_trend_v2", timeframe="4h", enabled=True),
        PaperSlot(strategy="mm200_trend_v2", timeframe="4h", enabled=True),
    ]
    with pytest.raises(ValueError, match="duplicada"):
        save_paper_slots(slots)


def test_save_paper_slots_rejects_more_than_three_enabled():
    slots = [
        PaperSlot(strategy="mm200_trend_v1", timeframe="4h", enabled=True),
        PaperSlot(strategy="mm200_trend_v2", timeframe="4h", enabled=True),
        PaperSlot(strategy="range_hunter_v1", timeframe="4h", enabled=True),
        PaperSlot(strategy="bb_squeeze_v1", timeframe="1d", enabled=True),
    ]
    with pytest.raises(ValueError, match="Máximo 3"):
        save_paper_slots(slots)
