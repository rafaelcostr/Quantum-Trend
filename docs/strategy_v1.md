# Strategy v1 — Range Hunter

## Market
- **Symbol:** BTC/USDT spot
- **Timeframe:** 4H
- **Mode:** Long-only (v1)

## Regime filter
- ADX(14) < 25 → market treated as ranging
- If ADX >= 25 → no new entries

## Entry (LONG)
All conditions required:
1. Close < Bollinger lower band (20, 2σ)
2. RSI(14) < 38
3. ADX(14) < 25
4. Optional: price within 1% of support (2+ touches in lookback)

## Exit
1. Stop: max(2.5% below entry, below support)
2. Target: Bollinger middle band (20 SMA)
3. Emergency: ADX > 35 (regime shift)

## Risk
- Risk per trade: 1% of equity
- Max 1 open position
- Entry on **next candle open** after signal

## Costs (backtest)
- Fee: 0.1% per side
- Slippage: 0.05% per side

## Implementation
- Code: `src/atlas/strategies/range_hunter_v1.py`
- Config: `config/backtest.yaml`
