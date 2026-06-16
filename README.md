# ATLAS QUANT

Modular crypto trading system: **backtest → paper → live** with the same strategy core.

## Quick start

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows

# Install
pip install -e ".[dev]"

# Start PostgreSQL (optional, for journal + candle storage)
docker compose up -d

# Download BTC/USDT 4H data
atlas research download

# Run backtest
atlas research backtest
```

## Structure

```
src/atlas/
├── core/           # models, indicators, risk, config
├── strategies/     # signal logic (pure)
├── brokers/        # simulated, binance demo/live
├── research/       # collector, backtester, statistics
├── runtime/        # runner, journal (paper/live)
└── cli.py
```

## Modes

| Command | Mode |
|---------|------|
| `atlas research backtest` | Historical simulation |
| `atlas trade paper` | Binance Demo (after runner phase) |
| `atlas trade live` | Real money (after promotion gates) |

See `docs/strategy_v1.md` and `docs/promotion_gates.md`.
