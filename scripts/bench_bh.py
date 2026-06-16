import pandas as pd

df = pd.read_parquet("data/cache/binance_BTCUSDT_4h.parquet")
s = df["close"].iloc[200]
e = df["close"].iloc[-1]
print(f"Period: {df.index[200]} -> {df.index[-1]}")
print(f"Buy & Hold: {(e/s - 1)*100:.2f}%")
print(f"BTC: ${s:,.0f} -> ${e:,.0f}")
