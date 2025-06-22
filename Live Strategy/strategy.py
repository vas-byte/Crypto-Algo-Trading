import time
import math
from datetime import datetime, timedelta
from binance.client import Client
import talib as ta
from sentiment import SentimentScraper 
import numpy as np
import asyncio
import pytz

class BinanceTradingBot:
    def __init__(self, api_key, api_secret, symbols, coin_names, trailing_stop_pct=0.05, trade_pct=0.2, slippage=0.01, live=True, deepseek_api_key=""):
        
        # Binance API client initialization
        self.client = Client(api_key, api_secret)
        self.coin_names = coin_names
        self.quote_asset = "USDT"

        # Initialize trading parameters
        self.symbols = symbols
        self.trailing_stop_pct = trailing_stop_pct
        self.trade_pct = trade_pct
        self.slippage_pct = slippage

        # Initialize bot state
        self.positions = {sym: False for sym in symbols}
        self.trailing_stops = {}
        self.last_candle_time = {sym: None for sym in symbols}
        self.interval = Client.KLINE_INTERVAL_1HOUR
        self.islive = live
        self.sentiment_scraper = SentimentScraper(deepseek_api_key)
        
        # Adelaide timezone
        adelaide_tz = pytz.timezone('Australia/Adelaide')
        self.last_scrape_time = datetime.now(adelaide_tz) - timedelta(minutes=40)

        # Initialize technical indicators
        self.ema = {}
        self.obv = {}
        self.obv_slope = {}
        self.macd = {}
        self.macdsignal = {}
        self.atr = {}
        self.atr_mean = {}
        self.sentiment = {}

        # Initialize array of closing prices for each symbol
        self.closing_prices = {sym: [] for sym in symbols}
        self.volume = {sym: [] for sym in symbols}
        self.high = {sym: [] for sym in symbols}
        self.low = {sym: [] for sym in symbols}

    def fetch_latest_candle(self, symbol):

        # Fetch the latest candle data for the given symbol
        klines = self.client.get_klines(symbol=symbol, interval=self.interval, limit=2)

        # Select the second last candle (the most recent completed candle)
        candle = klines[-2]

        # Adelaide timezone
        adelaide_tz = pytz.timezone('Australia/Adelaide')

        # Return a dictionary with the candle data
        return {
            'open_time': datetime.fromtimestamp(candle[0] / 1000, adelaide_tz),
            'open': float(candle[1]),
            'high': float(candle[2]),
            'low': float(candle[3]),
            'close': float(candle[4]),
            'volume': float(candle[5]),
            'close_time': datetime.fromtimestamp(candle[6] / 1000, adelaide_tz),
        }

    def strategy_decision(self, candle, symbol, in_pos):
        closing_price = candle['close']

        sentiment_long = self.sentiment[symbol] > 0.7
        sentiment_short = self.sentiment[symbol] < -0.5

        ema_long = self.ema[symbol] < closing_price
        ema_short = self.ema[symbol] > closing_price

        macd_long = self.macd[symbol] > self.macdsignal[symbol]
        macd_short = self.macd[symbol] < self.macdsignal[symbol]

        obv_long = self.obv_slope[symbol] > 0
        obv_short = self.obv_slope[symbol] < 0

        atr_entry = self.atr[symbol][-1] > self.atr_mean[symbol]

        long = (sentiment_long and ema_long and macd_long and obv_long and atr_entry)
        short = (sentiment_short and ema_short and macd_short and obv_short and atr_entry)

        if long:
            return 'buy'
        
        elif short:
            return 'sell'
        
        if not in_pos:
            return "nothing"
        
        if (not long and obv_short and macd_short):
            return 'close_long'
        
        elif (not short and obv_long and macd_long):
            return 'close_short'

    def get_symbol_filters(self, symbol):
        info = self.client.get_symbol_info(symbol)
        filters = {}
        for f in info['filters']:
            filters[f['filterType']] = f
        return filters
    
    def get_usdt_balance(self):

        # Fetch USDT balance from account that is available for trading
        balances = self.client.get_account()['balances']
        for b in balances:
            if b['asset'] == 'USDT':
                return float(b['free'])
        return 0.0

    def get_min_lot_size(self, symbol):

        # Fetch minimum lot size for the symbol
        info = self.client.get_symbol_info(symbol)
        for f in info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                return float(f['minQty'])
        return 0.001  # fallback if not found

    def quantity_from_usdt(self, symbol, usdt_amount):

        # Get price and minimum lot size for the symbol
        price = self.get_current_price(symbol)
        filters = self.get_symbol_filters(symbol)
        step_size = float(filters['LOT_SIZE']['stepSize'])
       
        # Calculate the quantity to buy based on USDT amount and current price
        qty = usdt_amount / price

        # Round quantity to precision based on minimum lot size
        precision = int(round(-math.log10(step_size)))
        qty = math.floor(qty * 10**precision) / 10**precision

        # return quantity
        return qty
    
    def quantity_for_close(self, quantity, symbol):

        # Get step size for the symbol
        filters = self.get_symbol_filters(symbol)
        step_size = float(filters['LOT_SIZE']['stepSize'])
        precision = int(round(-math.log10(step_size)))

        # Round quantity to the nearest step size
        qty = math.floor(quantity * 10**precision) / 10**precision
    
        return qty
        
    
    def get_limit_price(self, symbol, direction='buy'):
        filters = self.get_symbol_filters(symbol)
        tick_size = float(filters['PRICE_FILTER']['tickSize'])
        limit_price = 0
        if direction == 'buy':
            limit_price = self.get_current_price(symbol) * (1 + self.slippage_pct)
        elif direction == 'sell':
            limit_price = self.get_current_price(symbol) * (1 - self.slippage_pct)
        
        # Round limit price to the nearest tick size
        limit_price = math.floor(limit_price / tick_size) * tick_size
        return limit_price
    

    def long(self, symbol):

        # Get USDT balance
        usdt_balance = self.get_usdt_balance()

        # Calculate the amount in USDT to trade
        trade_usdt = usdt_balance * self.trade_pct

        # Calculate the quantity to buy based on the current price
        quantity = self.quantity_from_usdt(symbol, trade_usdt)

        # If quantity is less than the minimum lot size, skip the buy
        if quantity < self.get_min_lot_size(symbol):
            print(f"[{symbol}] Quantity {quantity} less than min lot size. Skipping buy.")
            return None, None

        try:
            print(f"[{symbol}] Placing BUY order for {quantity} {symbol[:-4]} (~{trade_usdt:.2f} USDT)")

            limit_price = self.get_limit_price(symbol, direction='buy')

            # Place a market buy order
            if self.islive:
                order = self.client.create_order(
                    symbol=symbol,
                    side='BUY',
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=quantity,
                    price=limit_price  
                )
            else:
                order = self.client.create_test_order(
                    symbol=symbol,
                    side='BUY',
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=quantity,
                    price=limit_price  
                )
            
            # Extract the price from the order response
            price = float(order['fills'][0]['price'])
            print(f"[{symbol}] BUY executed at {price}")
            return price, quantity
        
        except Exception as e:
            print(f"[{symbol}] BUY order failed: {e}")
            return None, None

    def close_long(self, symbol):
        try:

            asset = symbol.replace('USDT', '')

            # Get the quantity to close
            quantity = float(self.client.get_asset_balance(asset=asset)['free'])
            quantity = self.quantity_for_close(quantity, symbol)
            limit_price = self.get_limit_price(symbol, direction='sell')

            print(f"[{symbol}] Placing SELL order for {quantity} {symbol[:-4]}")

            # Place a market sell order
            if self.islive:
                order = self.client.create_order(
                    symbol=symbol,
                    side='SELL',
                    type='LIMIT',
                    quantity=quantity,
                    timeInForce='GTC',
                    price=limit_price 
                )
            else:
                order = self.client.create_test_order(
                    symbol=symbol,
                    side='SELL',
                    type='LIMIT',
                    quantity=quantity,
                    timeInForce='GTC',
                    price=limit_price 
                )

            # Extract the price from the order response
            price = float(order['fills'][0]['price'])
            print(f"[{symbol}] CLOSE SELL executed at {price}")
            return price
        
        except Exception as e:
            print(f"[{symbol}] CLOSE SELL order failed: {e}")
            return None
    

    def short(self, symbol):

        # Get USDT balance
        usdt_balance = self.get_usdt_balance()

        # Calculate the amount in USDT to trade
        trade_usdt = usdt_balance * self.trade_pct * 1.00

        # Calculate the quantity to sell based on the current price
        quantity = self.quantity_from_usdt(symbol, trade_usdt)

        # If quantity is less than the minimum lot size, skip the sell
        if quantity < self.get_min_lot_size(symbol):
            print(f"[{symbol}] Quantity {quantity} less than min lot size. Skipping buy.")
            return None, None
        
        # Get the base asset from the symbol (e.g., DOGE for DOGEUSDT)
        base_asset = symbol.replace('USDT', '')
        
        try:
            # Borrow the asset on isolated margin
            if self.islive:
               
                # Transfer USDT collateral to isolated margin account
                transfer = self.client.transfer_spot_to_isolated_margin(
                    asset=self.quote_asset,
                    amount=trade_usdt,
                    symbol=symbol)
                
                # Borrow the asset
                borrow = self.client.create_margin_loan(
                    asset=base_asset,
                    amount=quantity,
                    isIsolated='TRUE',
                    symbol=symbol
                )

            print(f"Borrowed {quantity} {base_asset} on isolated margin for {symbol}")

            limit_price = self.get_limit_price(symbol, direction='sell')

            # Sell the borrowed asset
            if self.islive:
                order = self.client.create_margin_order(
                    symbol=symbol,
                    side='SELL',
                    type='LIMIT',
                    quantity=quantity,
                    price=limit_price,
                    timeInForce='GTC',
                    isIsolated='true'
                )

                # Extract the price from the order response
                price = float(order['fills'][0]['price'])
                print(f"[{symbol}] MARGIN SELL executed at {price}")
                return price, quantity
            else:
                print(f"{symbol } MARGIN SELL signal (test mode)")
                return limit_price, quantity
        
    
        except Exception as e:
            print(f"[{symbol}] MARGIN SELL order failed: {e}")
            return None, None


    def close_short(self, symbol):

        base_asset = symbol.replace('USDT', '')

        try:

            # Buy back the asset
            limit_price = self.get_limit_price(symbol, direction='buy')

            if self.islive:

                # Get the quantity to close
                margin_account = self.client.get_isolated_margin_account(symbol=symbol)
                qty = float(margin_account['assets'][0]['baseAsset']['borrowed'])  # Get the borrowed amount
                qty += float(margin_account['assets'][0]['baseAsset']['interest'])  # Add interest to the borrowed amount
                buy_qty = self.quantity_for_close(qty, symbol)

                filters = self.get_symbol_filters(symbol)
                step_size = float(filters['LOT_SIZE']['stepSize'])

                # Ensure we buy at enough to conver borrowed amount and interest
                if buy_qty < qty:
                    buy_qty += step_size

                order = self.client.create_margin_order(
                    symbol=symbol,
                    side='BUY',
                    quantity=buy_qty,
                    isIsolated='TRUE',
                    type='LIMIT',
                    timeInForce='GTC',
                    price=limit_price
                )

            print(f"[{symbol}] MARGIN BUY executed to close short position")

            if self.islive:

                # Repay the loan on isolated margin
                repay = self.client.repay_margin_loan(
                    asset=base_asset,
                    amount=buy_qty,
                    isIsolated='TRUE',
                    symbol=symbol
                )

                # Transfer collateral back to spot account
                margin_account = self.client.get_isolated_margin_account(symbol=symbol)

                # Transfer USDT back to spot account
                transfer_usdt = margin_account['assets'][0]['quoteAsset']['netAsset']

                transfer = self.client.transfer_isolated_margin_to_spot(
                    asset=self.quote_asset,
                    amount=transfer_usdt,
                    symbol=symbol
                )

                # Transfer base asset back to spot account
                transfer_base = margin_account['assets'][0]['baseAsset']['netAsset']

                transfer = self.client.transfer_isolated_margin_to_spot(
                    asset=base_asset,
                    amount=transfer_base,
                    symbol=symbol
                )

            print(f"Repaid {buy_qty} {base_asset} loan")

            if self.islive:
                # Extract the price from the order response
                price = float(order['fills'][0]['price'])
                print(f"[{symbol}] CLOSE SELL executed at {price}")
                return price
            else:
                print(f"{symbol} CLOSE SELL signal (test mode)")
                return limit_price
        
        except Exception as e:
            print(f"Error closing short: {e}")


    def get_current_price(self, symbol):

        # Fetch the current ticker price for the symbol
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker['price'])

    def update_trailing_stop(self, symbol, current_price):

        # If no trailing stop exists for this symbol, return (i.e., no position)
        if symbol not in self.trailing_stops:
            return

        ts = self.trailing_stops[symbol]
        is_short = ts['direction'] == 'short'

        if not is_short:

            stop_price = ts['highest_price'] * (1 - self.trailing_stop_pct)

            # If price has increased, update the highest price
            if current_price > ts['highest_price']:
                ts['highest_price'] = current_price
                print(f"[{symbol}] New highest price for trailing stop: {current_price:.4f}")

                # Calculate the trailing stop price
                stop_price = ts['highest_price'] * (1 - self.trailing_stop_pct)

            # If current price is less than or equal to the stop price, trigger the trailing stop
            if current_price <= stop_price:
                print(f"[{symbol}] Trailing stop triggered! Current price: {current_price:.4f}, stop price: {stop_price:.4f}")

                sell_price = self.close_long(symbol)

                if sell_price:
                    self.positions[symbol] = False
                    del self.trailing_stops[symbol]

        else:

            stop_price = ts['lowest_price'] * (1 + self.trailing_stop_pct)

            # If price has decreased, update the lowest price
            if current_price < ts['lowest_price']:
                ts['lowest_price'] = current_price
                print(f"[{symbol}] New lowest price for trailing stop: {current_price:.4f}")

                # Calculate the trailing stop price
                stop_price = ts['lowest_price'] * (1 + self.trailing_stop_pct)

            # If current price is greater than or equal to the stop price, trigger the trailing stop
            if current_price >= stop_price:
                print(f"[{symbol}] Trailing stop triggered! Current price: {current_price:.4f}, stop price: {stop_price:.4f}")

                buy_price = self.close_short(symbol)

                if buy_price:
                    self.positions[symbol] = False
                    del self.trailing_stops[symbol]


    def get_initial_indicators(self):
        
        # For each symbol, initialize indicators
        for sym in self.symbols:

            # Get past 50 candles for initial indicators
            klines = self.client.get_klines(symbol=sym, interval=self.interval, limit=100)
            closes = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            closes = np.array(closes)
            volumes = np.array(volumes)
            highs = np.array(highs)
            lows = np.array(lows)

            # Update closing price and volume arrays
            self.closing_prices[sym] = closes
            self.volume[sym] = volumes
            self.high[sym] = highs
            self.low[sym] = lows

            # Calculate initial indicators
            self.ema[sym] = ta.EMA(closes, timeperiod=50)[-1]
            self.obv[sym] = ta.OBV(closes, volumes)
            self.obv_slope[sym] = ta.LINEARREG_SLOPE(self.obv[sym], timeperiod=14)[-1]
            self.macd[sym] = ta.MACD(closes, fastperiod=12, slowperiod=26, signalperiod=9)[0][-1]
            self.macdsignal[sym] = ta.MACD(closes, fastperiod=12, slowperiod=26, signalperiod=9)[1][-1]
            self.atr[sym] = ta.ATR(highs, lows, closes, timeperiod=14)
            self.atr_mean[sym] = ta.SMA(self.atr[sym], timeperiod=50)[-1]
            
            # Placeholder for sentiment analysis
            self.sentiment[sym] = 0  

    def update_indicators(self, symbol, candle):

        # Update indicators with the latest candle
        self.closing_prices[symbol] = np.append(self.closing_prices[symbol], candle['close'])
        self.volume[symbol] = np.append(self.volume[symbol], candle['volume'])
        self.high[symbol] = np.append(self.high[symbol], candle['high'])
        self.low[symbol] = np.append(self.low[symbol], candle['low'])

        # Recalculate indicators
        self.ema[symbol] = ta.EMA(self.closing_prices[symbol], timeperiod=50)[-1]
        self.obv[symbol] = np.append(self.obv[symbol], ta.OBV(self.closing_prices[symbol], self.volume[symbol])[-1])
        self.obv_slope[symbol] = ta.LINEARREG_SLOPE(self.obv[symbol], timeperiod=14)[-1]
        self.macd[symbol] = ta.MACD(self.closing_prices[symbol], fastperiod=12, slowperiod=26, signalperiod=9)[0][-1]
        self.macdsignal[symbol] = ta.MACD(self.closing_prices[symbol], fastperiod=12, slowperiod=26, signalperiod=9)[1][-1]
        self.atr[symbol] = np.append(self.atr[symbol], ta.ATR(self.high[symbol], self.low[symbol], self.closing_prices[symbol], timeperiod=14)[-1])
        self.atr_mean[symbol] = ta.SMA(self.atr[symbol], timeperiod=50)[-1]


    async def run(self):
        
        # Initialize indicators for all symbols
        self.get_initial_indicators()

        # Login
        await self.sentiment_scraper.login()

        while True:
            
            # check sentiment auth
            await self.sentiment_scraper.check_auth()

            # Get current time
            adelaide_tz = pytz.timezone('Australia/Adelaide')

            # Get current time in Adelaide
            now = datetime.now(adelaide_tz)

            # Iterate through each symbol
            for symbol in self.symbols:
                
                # before the hour, update sentiment
                if (now.minute >= 17 and now.minute <= 33 and now - self.last_scrape_time >= timedelta(minutes=40)):
                    print(f"[{symbol}] Fetching sentiment data...")
                    name = self.coin_names[symbol]

                    try:
                        self.sentiment[symbol] = await self.sentiment_scraper.get_sentiment(symbol[:-4], name)
                    except Exception as e:
                        print(f"[{symbol}] Error fetching sentiment: {e}")
                        self.sentiment[symbol] = 0  # Default to neutral sentiment
                    
                    # On the last symbol, update the last scrape time
                    if symbol == "XRPUSDT":
                        self.last_scrape_time = now

                # Check if an hour has passed since last candle processed
                if (self.last_candle_time[symbol] is None) or (now >= self.last_candle_time[symbol] + timedelta(hours=1)):
                    
                    # Fetch the latest candle
                    candle = self.fetch_latest_candle(symbol)
                    self.last_candle_time[symbol] = candle['close_time']

                    # Check if we are in a position for this symbol
                    in_position = self.positions[symbol]

                    # Update indicators with the latest candle
                    self.update_indicators(symbol, candle)

                    # Make a trading decision based on the strategy
                    decision = self.strategy_decision(candle, symbol, in_position)
                    print(f"[{symbol}] Decision: {decision} at {candle['close_time']}")

                    # If decision is to buy, check if we are not already in a position
                    if decision == 'buy' and not in_position:

                        # Place a buy order
                        price, quantity = self.long(symbol)

                        # If buy was successful, update position and trailing stop
                        if price and quantity:
                            self.positions[symbol] = True
                            self.trailing_stops[symbol] = {
                                'highest_price': price,
                                'quantity': quantity,
                                'symbol': symbol,
                                'direction': 'long'
                            }

                    # If decision is to sell, check if we are in a position
                    elif decision == 'close_long' and in_position:

                        # Check if we are long
                        if self.trailing_stops[symbol]['direction'] != 'long':
                            print(f"[{symbol}] Not in a long position, cannot close long.")
                            continue

                        # Get the quantity and close the position
                        quantity = self.trailing_stops[symbol]['quantity']
                        price = self.close_long(symbol)

                        # Update state if sell was successful
                        if price:
                            self.positions[symbol] = False
                            self.trailing_stops.pop(symbol, None)

                    elif decision == 'sell' and not in_position:
                        # Place a short order
                        price, quantity = self.short(symbol)

                        # If short was successful, update position and trailing stop
                        if price and quantity:
                            self.positions[symbol] = True
                            self.trailing_stops[symbol] = {
                                'lowest_price': price,
                                'quantity': quantity,
                                'symbol': symbol,
                                'direction': 'short'
                            }
                    
                    elif decision == 'close_short' and in_position:

                        # Check if we are short
                        if self.trailing_stops[symbol]['direction'] != 'short':
                            print(f"[{symbol}] Not in a short position, cannot close short.")
                            continue
                            
                        # Get the quantity and close the short position
                        price = self.close_short(symbol)

                        # Update state if sell was successful
                        if price:
                            self.positions[symbol] = False
                            self.trailing_stops.pop(symbol, None)

            # Check trailing stops every minute for all positions
            for symbol in list(self.trailing_stops.keys()):
                current_price = self.get_current_price(symbol)
                self.update_trailing_stop(symbol, current_price)

            # sleep 1 minute before next iteration
            time.sleep(60)  

if __name__ == "__main__":
    API_KEY = ''
    API_SECRET = ''
    
    SYMBOLS = ['DOGEUSDT', 'TRUMPUSDT', 'BTCUSDT', 'ADAUSDT', 'XRPUSDT']

    COINNAMES = {'DOGEUSDT': 'dogecoin', 'TRUMPUSDT': 'trump coin',
                 'BTCUSDT': 'bitcoin', 'XRPUSDT': 'ripple', 'ADAUSDT': 'cardano'}
    
    DEEPSEEK_API_KEY = ''
    LIVE = True
    TRAILING_STOP_PCT = 0.05
    TRADE_PCT = 0.2
    SLIPPAGE = 0.01
    
    bot = BinanceTradingBot(API_KEY, API_SECRET, SYMBOLS, COINNAMES,
                            TRAILING_STOP_PCT, TRADE_PCT, SLIPPAGE, 
                            live=LIVE, deepseek_api_key=DEEPSEEK_API_KEY)
    
    asyncio.run(bot.run())
