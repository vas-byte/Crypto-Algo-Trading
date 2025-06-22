from binance.client import Client
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# === CONFIG ===
api_key = ''
api_secret = ''
client = Client(api_key, api_secret)

# === SYMBOLS ===
symbols_raw = '''
ADA/USDT BTC/USDT DOGE/USDT ETH/USDT SOL/USDT XMR/USDT XRP/USDT
'''

symbols = [s.replace('/', '') for s in symbols_raw.strip().split()]

# === INTERVALS ===
intervals = [
    Client.KLINE_INTERVAL_1MINUTE,
    Client.KLINE_INTERVAL_5MINUTE,
    Client.KLINE_INTERVAL_15MINUTE,
    Client.KLINE_INTERVAL_1HOUR,
    Client.KLINE_INTERVAL_4HOUR,
    Client.KLINE_INTERVAL_1DAY,
]

# === TIME RANGE ===
start_str = "2024-01-01"
end_str = "2024-12-31"

# === Ensure Data folder exists ===
os.makedirs("Data", exist_ok=True)

# === Fetch function ===
def fetch_and_save(symbol, interval):
    try:
        print(f"\n📥 Fetching {symbol} | Interval: {interval}")
        klines = client.get_historical_klines(symbol, interval, start_str, end_str)

        if not klines:
            print(f"⚠️ No data for {symbol} at interval {interval}")
            return

        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'num_trades',
            'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')

        safe_interval = interval.replace(" ", "_")
        filename = f"{symbol}_{safe_interval}.csv"

        df.to_csv(filename, index=False)
        print(f"✅ Saved {len(df)} rows to {filename}")

        # To avoid rate limit abuse — apply per-thread delay
        time.sleep(0.5)

    except Exception as e:
        print(f"❌ Error for {symbol} at {interval}: {e}")
        time.sleep(2)


# === Multithread the tasks ===
tasks = [(symbol, interval) for symbol in symbols for interval in intervals]

# Limit thread count to avoid Binance bans (recommend <=10)
with ThreadPoolExecutor(max_workers=7) as executor:
    futures = [executor.submit(fetch_and_save, sym, intv) for sym, intv in tasks]

    for future in as_completed(futures):
        future.result()  # re-raise exceptions if any
