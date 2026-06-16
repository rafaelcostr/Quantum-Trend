"""Quick Binance Demo connectivity check. Run: python scripts/check_binance_demo.py"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

import ccxt  # noqa: E402


def main() -> int:
    key = os.getenv("BINANCE_DEMO_API_KEY", "").strip()
    secret = os.getenv("BINANCE_DEMO_API_SECRET", "").strip()

    print("=== Binance Demo diagnostic ===")
    print(f".env found: {(ROOT / '.env').is_file()}")
    print(f"API key length: {len(key)} (expect ~64)")
    print(f"Secret length: {len(secret)} (expect ~64)")

    if not key or not secret:
        print("FAIL: BINANCE_DEMO_API_KEY or BINANCE_DEMO_API_SECRET empty in .env")
        return 1

    ex = ccxt.binance({"apiKey": key, "secret": secret, "enableRateLimit": True})
    ex.enable_demo_trading(True)
    api_url = ex.urls.get("api", {})
    print(f"REST URL: {api_url.get('public') or api_url}")

    print("\n1) Public candles (no auth)...")
    try:
        rows = ex.fetch_ohlcv("BTC/USDT", "4h", limit=2)
        print(f"   OK — got {len(rows)} candles, last close={rows[-1][4]}")
    except Exception as exc:
        print(f"   FAIL — {type(exc).__name__}: {exc}")
        return 1

    print("\n2) Private balance (needs valid key + IP + permissions)...")
    try:
        bal = ex.fetch_balance()
        usdt = bal.get("USDT", {}).get("free")
        print(f"   OK — USDT free={usdt}")
    except Exception as exc:
        print(f"   FAIL — {type(exc).__name__}: {exc}")
        print("\nLikely fixes:")
        print("  - Create key at https://demo.binance.com (not binance.com)")
        print("  - Add your public IP to the key whitelist")
        print("  - Enable: Reading + Spot trading")
        print("  - Regenerate key if secret was copied wrong")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
