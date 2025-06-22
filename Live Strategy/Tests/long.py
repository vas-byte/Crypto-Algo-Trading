import time
import math
from datetime import datetime, timedelta
from binance.client import Client
import talib as ta
import numpy as np
import asyncio
import pytz
import decimal
symbol = "XRPUSDT"
usdt_amount = 10  # Amount in USDT to invest

API_KEY = 'Pd4mCn4tqyjrPTZ2rSt8J62ohvjyDKNKGSNZrXPZDmKNqWqheoMGN6PmoM5XsLGl'
API_SECRET = 'PQQeIZLvDgQNJBP8mDciGMLMdcGBVhSWTaqPbTsiNVwgjrhjiUPqXG1tOYIfhe3K'

# --- Initialize client ---
client = Client(api_key=API_KEY, api_secret=API_SECRET)

# --- Helper Functions ---
def get_symbol_filters(symbol):
    info = client.get_symbol_info(symbol)
    filters = {}
    for f in info['filters']:
        filters[f['filterType']] = f
    return filters

def get_current_price(symbol):
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

def round_step_size(value, step_size):
    precision = int(round(-math.log10(float(step_size))))
    return math.floor(float(value) * 10**precision) / 10**precision

# --- Main Execution ---
filters = get_symbol_filters(symbol)
min_qty = float(filters['LOT_SIZE']['minQty'])
step_size = float(filters['LOT_SIZE']['stepSize'])
tick_size = float(filters['PRICE_FILTER']['tickSize'])
print(step_size, tick_size)

# Get current price
price = get_current_price(symbol)

# Calculate and round quantity
raw_qty = usdt_amount / price
qty = round_step_size(raw_qty, step_size)

# Prepare and round limit price for BUY (1% above current price)
limit_price_buy = round_step_size(price * 1.01, tick_size)

# Place BUY limit order
order_buy = client.create_order(
    symbol=symbol,
    side='BUY',
    type='LIMIT',
    timeInForce='GTC',
    quantity=qty,
    price=str(limit_price_buy)
)
print("Buy Order Placed:", order_buy)

# # Wait a moment before placing the sell order (optional)
time.sleep(2)

# Get updated price and prepare SELL at 1% below price
price = get_current_price(symbol)
limit_price_sell = round_step_size(price * 0.99, tick_size)

asset = symbol.replace('USDT', '')
quantity_sell = float(client.get_asset_balance(asset=asset)['free'])
qty_sell = round_step_size(quantity_sell, step_size)

print(qty_sell)

# Place SELL limit order
order_sell = client.create_order(
    symbol=symbol,
    side='SELL',
    type='LIMIT',
    timeInForce='GTC',
    quantity=qty_sell,
    price=str(limit_price_sell)
)

print("Sell Order Placed:", order_sell)



      