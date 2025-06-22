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
limit_price_sell = round_step_size(price * 0.99, tick_size)

asset = symbol.replace('USDT', '')

transfer = client.transfer_spot_to_isolated_margin(
    asset="USDT",
    amount=qty,
    symbol=symbol)

borrow = client.create_margin_loan(
                    asset=asset,
                    amount=qty,
                    isIsolated='TRUE',
                    symbol=symbol
                )

print(f"Borrowed {qty} {asset} on isolated margin for {symbol}")

# Sell the borrowed asset          
order = client.create_margin_order(
    symbol=symbol,
    side='SELL',
    type='LIMIT',
    quantity=qty,
    price=limit_price_sell,
    timeInForce='GTC',
    isIsolated='true'
)

print(f"Placed SELL order for {qty} {asset} at {limit_price_sell} USDT")

# Wait for the order to fill
time.sleep(10)  # Adjust sleep time as needed

# Buy back the asset at a lower price
price = get_current_price(symbol)
limit_price_buy = round_step_size(price * 1.01, tick_size)

# Calculate the quantity to buy back
margin_account = client.get_isolated_margin_account(symbol=symbol)
qty = float(margin_account['assets'][0]['baseAsset']['borrowed'])  # Get the borrowed amount
qty += float(margin_account['assets'][0]['baseAsset']['interest'])  # Add interest to the borrowed amount
buy_qty = round_step_size(qty, step_size)

if buy_qty < qty:
    buy_qty += step_size  # Ensure we buy at least the minimum quantity

# Create a BUY order to close the position
order_buy = client.create_margin_order(
    symbol=symbol,
    side='BUY',
    type='LIMIT',
    quantity=buy_qty,
    price=limit_price_buy,
    timeInForce='GTC',
    isIsolated='true'
)

print(f"Placed BUY order for {buy_qty} {asset} at {limit_price_buy} USDT")

# Wait for the buy order to fill
time.sleep(10)  # Adjust sleep time as needed

# Repay the borrowed asset
repay = client.repay_margin_loan(
    asset=asset,
    amount=buy_qty,
    isIsolated='TRUE',
    symbol=symbol
)

print(f"Repaid {buy_qty} {asset} on isolated margin for {symbol}")
# Check the margin account balance
margin_account = client.get_isolated_margin_account(symbol=symbol)

transfer_usdt = margin_account['assets'][0]['quoteAsset']['netAsset']
transfer = client.transfer_isolated_margin_to_spot(
    asset='USDT',
    amount=transfer_usdt,
    symbol=symbol
)

transfer_xrp = margin_account['assets'][0]['baseAsset']['netAsset']
transfer = client.transfer_isolated_margin_to_spot(
    asset=asset,
    amount=transfer_xrp,
    symbol=symbol
)
print(f"Transferred {transfer_usdt} USDT and {transfer_xrp} {asset} to spot account for {symbol}")


      