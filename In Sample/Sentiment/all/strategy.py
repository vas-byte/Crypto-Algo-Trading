import datetime
import os
import backtrader as bt
from tabulate import tabulate
import numpy as np
import sys
import pandas as pd
import backtrader as bt
import pandas as pd
import math

### TODO ###
# - adding news to sentiment indicator worsens the performance
# - Reddit, better using r/btc r/bitcoinmarkets (r/bitcoin even better), 
#  r/ethtrader r/ethereum is worse , r/dogecoin is worse, r/monero r/xmrtrader is worse, 
#  r/cryptomarkets is worse, r/cryptocurrency is worse, r/ripple r/xrp is slightly better
#  r/cardano is worse, r/solana is better
# Note XMR has k of 0.01
# - try out of sample testing (2024 data, no reddit, no news)

class OBVSlope(bt.Indicator):
    lines = ('slope',)
    params = (('period', 14),)

    def __init__(self):
        obv = bt.talib.OBV(self.data.close, self.data.volume)
        self.lines.slope = bt.talib.LINEARREG_SLOPE(obv, timeperiod=self.p.period)

class CachedIndicator(bt.Indicator):
    lines = ('sentiment',)
    params = (('cache_file', 'path/to/your/cache_file.csv'),)

    def __init__(self):
        if os.path.exists(self.p.cache_file):
            self.cache = pd.read_csv(self.p.cache_file, parse_dates=True, index_col='Date')
            self.idx = 0
       
    
    def next(self):
        # Match by current date and time
        dt = self.data.datetime.datetime(0)
        if self.idx < len(self.cache) and self.cache.index[self.idx] == dt:
            self.lines.sentiment[0] = self.cache['Sentiment_All'].iloc[self.idx]
            self.idx += 1

class SentimentIndicator(bt.Indicator):
    lines = ('sentiment',)
    params = (
        ('ticker', 'ADA'),
        ('crypto', 'cardano'),   
        ('reddit_folders', []),
        ('k', 100),
        ('double_dot', True)
    )

    def __init__(self):
        double_dot = '../..'

        if not self.p.double_dot:
            double_dot = '..'

        self.twitter = pd.read_csv(f'{double_dot}/Data/Twitter/{self.p.ticker}/twitter_deepseek_relevant.csv', parse_dates=True, date_parser=lambda x: pd.to_datetime(x, format="%a %b %d %H:%M:%S %z %Y"), index_col='created_at')
        
        # Load Reddit data
        self.reddit = pd.read_csv(f'{double_dot}/Data/Reddit/crypto_currency_news/sentiment_deepseek.csv', parse_dates=True)
        self.reddit['created'] = pd.to_datetime(self.reddit['created'], unit='s')
        
        # Load more Reddit data for cryptocurrency trading
        cryptotrading = pd.read_csv(f'{double_dot}/Data/Reddit/cryptocurrencytrading/sentiment_deepseek.csv', parse_dates=True)
        cryptotrading['created'] = pd.to_datetime(cryptotrading['created'], unit='s')
        cryptomarkets = pd.read_csv(f'{double_dot}/Data/Reddit/cryptomarkets/sentiment_deepseek.csv', parse_dates=True)
        cryptomarkets['created'] = pd.to_datetime(cryptomarkets['created'], unit='s')

        # Merge the two Reddit datasets
        self.reddit = pd.concat([self.reddit, cryptotrading, cryptomarkets], ignore_index=True)

        # Load individual subreddits for specific cryptocurrencies
        for folder in self.p.reddit_folders:
            subreddit_data = pd.read_csv(f'{double_dot}/Data/Reddit/{folder}/sentiment_deepseek.csv', parse_dates=True)
            subreddit_data['created'] = pd.to_datetime(subreddit_data['created'], unit='s')
            self.reddit = pd.concat([self.reddit, subreddit_data], ignore_index=True)

        self.news = pd.read_csv(f'{double_dot}/Data/news_deepseek.csv', parse_dates=True)
        self.news['date'] = pd.to_datetime(self.news['date'], format="%Y-%m-%d %H:%M:%S")
    
    def tanh_scale(self, x, k):
        return np.tanh(k * x)
    
    def next(self):
        dt = self.data.datetime.datetime(0)
        df = self.twitter

        # Filter tweets for current datetime
        tweets = df.loc[(df.index.date == dt.date()) & (df.index.time <= dt.time())]

        # Filter based on keywords and confidence
        filtered = tweets[
            # (tweets['confidence'] > self.p.min_confidence) &
            (tweets['clean_text'].str.contains(f'{self.p.ticker}|{self.p.crypto}', case=False, na=False))
        ]

        # Assign sentiment values
        sentiments = filtered['sentiment'].map({'Positive': 1, 'Negative': -1}).fillna(0).tolist()

        # Assign weights based on the number of retweets, likes, and replies
        weights = []
        for i in range(len(sentiments)):
            retweets = filtered.iloc[i]['retweet_count']
            likes = filtered.iloc[i]['favorite_count']
            followers = filtered.iloc[i]['followers']
            weight = followers * ((likes+1)/(followers+1)) * (retweets+1)
            weights.append(weight)

        # For reddit, filter
        df_reddit = self.reddit
        df_reddit = df_reddit.loc[(df_reddit['created'].dt.date == dt.date()) & (df_reddit['created'].dt.time <= dt.time())]
        df_reddit = df_reddit[df_reddit['combined_text'].str.contains(f'{self.p.ticker}|{self.p.crypto}', case=False, na=False)]
      
        # For each reddit post, assign sentiment values
        reddit_weights = []
        reddit_sentiments = []

        for _, row in df_reddit.iterrows():
            score = row['score']
            weight = score
            reddit_weights.append(weight)
            sentiment = 1 if row['sentiment'] == 'Positive' else -1 if row['sentiment'] == 'Negative' else 0
            reddit_sentiments.append(sentiment)
        
        # Now get news sentiment
        df_news = self.news
        df_news = df_news.loc[(df_news['date'].dt.date == dt.date()) & (df_news['date'].dt.time <= dt.time())]
        df_news = df_news[df_news['clean_text'].str.contains(f'{self.p.ticker}|{self.p.crypto}', case=False, na=False)]
       
        # For each news article, assign sentiment values
        news_sentiments = []
        for _, row in df_news.iterrows():
            sentiment = 1 if row['sentiment'] == 'Positive' else -1 if row['sentiment'] == 'Negative' else 0
            news_sentiments.append(sentiment)

        # Calculate weighted sentiment
        twitter_sentiment = sum(w * s for w, s in zip(weights, sentiments))

        # Calculate reddit sentiment
        reddit_sentiment = sum(w * s for w, s in zip(reddit_weights, reddit_sentiments))

        # Calculate news sentiment
        news_sentiment = np.mean(news_sentiments) if news_sentiments else 0

        # Normalize the sentiment
        sentiment_score = twitter_sentiment * 0.4 + reddit_sentiment * 0.4 + news_sentiment * 0.2

        # print(f"Twitter Sentiment: {twitter_sentiment}, Reddit Sentiment: {reddit_sentiment}, News Sentiment: {news_sentiment}, Sentiment Score: {sentiment_score}")
        sentiment_weighted = min(self.tanh_scale(sentiment_score, self.p.k),1)

        # Calculate the final sentiment
        self.lines.sentiment[0] = sentiment_weighted


class Sentiment(bt.Strategy):
    params = (
        ('MAL', 20),
        ('normalize', 50),
        ('stop_loss', 0.05),
        ('can_short', True),
        ('cryptoname', 'dogecoin'),
        ('k', 0.000001),
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        ('atr_period', 14),
        ('obv_period', 14),
        ('reddit_folders', []),
        ('hours', ''),
        ('sentiment_positive', 0.7),
        ('sentiment_negative', -0.5),
        ('atr_mean_period', 50),
    )

    def __init__(self):
       
        self.ema_mal = {}
        self.obv_slope = {}
        self.macd = {}
        self.atr = {}
        self.atr_mean = {}

        self.sentiment = {}
        
        self.trades = {}
        self.exit = {}
       
        self.equity = []
        self.max_drawdown = 0
        self.peak_equity = 0

        self.current_dir = ""

        self.order_groups = {}
        self.days = 0

        self.idx = 0

    def start(self):
        for data in self.datas:
            
            # EMA indicator
            self.ema_mal[data] = bt.talib.EMA(data.close, timeperiod=self.p.MAL)

            # OBV slope indicator
            self.obv_slope[data] = OBVSlope(data, period=self.p.obv_period)
            
            # MACD indicator
            self.macd[data] = bt.talib.MACD(data.close, fastperiod=self.p.macd_fast, slowperiod=self.p.macd_slow, signalperiod=self.p.macd_signal)

            # ATR indicator
            self.atr[data] = bt.talib.ATR(data.high, data.low, data.close, timeperiod=self.p.atr_period)

            # ATR mean indicator
            self.atr_mean[data] = bt.talib.SMA(self.atr[data], timeperiod=self.p.atr_mean_period)
           
            # Initialize the trades and exit lists for each data stream
            self.trades[data._name] = []
            self.exit[data._name] = []

            # Initialize the sentiment indicator for each data stream
            name = data._name.replace('USDT', '')

            if os.path.exists(f"../sentiment cache/{data._name}_{self.p.hours}_sentiment.csv"):
                sentiment_f =f"../sentiment cache/{data._name}_{self.p.hours}_sentiment.csv"
                self.sentiment[data] = CachedIndicator(cache_file=sentiment_f)
            else:
                self.sentiment[data] = SentimentIndicator(ticker=name, crypto=self.p.cryptoname, k=self.p.k, reddit_folders=self.p.reddit_folders)

        for stream in self.datas:
            self.order_groups[stream._name] = []


    def size_position(self, crypto):

        # Get the current price of the crypto
        current_price = crypto.close[0] + crypto.close[0] * 0.001

        # Calculate the size of the position based on the available cash and the current price
        available_cash = self.broker.getcash() * 0.2

        size = available_cash / current_price

        return size
        

    def next(self):

        # Skip the first few bars to normalize the indicators
        normalize = [self.p.MAL, self.p.macd_fast, self.p.macd_slow, self.p.macd_signal, self.p.obv_period, self.p.atr_period + self.p.atr_mean_period]

        if self.days < max(normalize):
            self.days += 1
            return
        
        for crypto in self.datas:
            
            sentiment_long = self.sentiment[crypto].lines.sentiment[0] > self.p.sentiment_positive
            sentiment_short = self.sentiment[crypto].lines.sentiment[0] < self.p.sentiment_negative

            ema_long = self.ema_mal[crypto][0] < crypto.close[0]
            ema_short = self.ema_mal[crypto][0] > crypto.close[0]

            macd_long = self.macd[crypto].macd[0] > self.macd[crypto].macdsignal[0]
            macd_short = self.macd[crypto].macd[0] < self.macd[crypto].macdsignal[0]

            obv_long = self.obv_slope[crypto][0] > 0
            obv_short = self.obv_slope[crypto][0] < 0

            atr_entry = self.atr[crypto][0] > self.atr_mean[crypto][0]

            long = (sentiment_long and ema_long and macd_long and obv_long and atr_entry)
            short = (sentiment_short and ema_short and macd_short and obv_short and atr_entry)
         
            # Issue a buy order if the conditions are met
            if long:
            
                if self.getposition(crypto).size < 0:
                    self.cancel_limit_orders(crypto=crypto)
                    self.close(data=crypto)
                  
                stop_price = crypto.close[0] * (1 - self.p.stop_loss)

                if self.getposition(crypto).size <= 0:
                    order = self.buy(data=crypto, size=self.size_position(crypto), transmit=False)
                    # stop_loss_order = self.sell(data=crypto, size=self.size_position(crypto), price=stop_price, exectype=bt.Order.Stop, parent=order, transmit=True)
                    stop_loss_order = self.sell(data=crypto, size=self.size_position(crypto), exectype=bt.Order.StopTrail, parent=order, transmit=True, trailpercent=self.p.stop_loss)
                    self.order_groups[crypto._name].append([order, stop_loss_order])
                    
            # Issue a sell order if the conditions are met
            elif short:

                if self.getposition(crypto).size > 0:
                    # If the current position is long, cancel all limit orders and close the position
                    self.cancel_limit_orders(crypto=crypto)
                    self.close(data=crypto)
                    
                stop_price = crypto.close[0] * (1 + self.p.stop_loss)              
                    
                if self.getposition(crypto).size >= 0 and self.p.can_short:
                    order = self.sell(data=crypto, size=self.size_position(crypto), transmit=False)
                    # stop_loss_order = self.buy(data=crypto, size=self.size_position(crypto), price=stop_price, exectype=bt.Order.Stop, parent=order, transmit=True)
                    stop_loss_order = self.buy(data=crypto, size=self.size_position(crypto), exectype=bt.Order.StopTrail, parent=order, transmit=True, trailpercent=self.p.stop_loss)
                    self.order_groups[crypto._name].append([order, stop_loss_order])

            # Close the long position (exit signal)
            elif self.getposition(crypto).size > 0 and (not long) and (obv_short and macd_short):
                self.cancel_limit_orders(crypto=crypto)
                self.close(data=crypto)

            # Close the short position (exit signal)
            elif self.getposition(crypto).size < 0 and (not short) and (obv_long and macd_long):
                self.cancel_limit_orders(crypto=crypto)
                self.close(data=crypto)
                    
            current_equity = self.broker.getvalue()
            self.equity.append(current_equity)
            self.peak_equity = max(self.peak_equity, current_equity)
            drawdown = (self.peak_equity - current_equity) / self.peak_equity
            self.max_drawdown = max(self.max_drawdown, drawdown)

    
    def notify_order(self, order : bt.Order):
      
        if order.status in [order.Completed]:

            # Append the order to the trades list
            if order.isbuy():
                self.trades[order.data._name].append({
                    'ref': order.ref,
                    'date': bt.num2date(order.executed.dt),
                    'size': order.executed.size,
                    'price': order.executed.price,
                    'pnl': order.executed.pnl,
                    'direction': "long",
                    'type': order.exectype,
                    'parent': order.parent.ref if order.parent else '-1'
                })
            
            elif order.issell():
                self.trades[order.data._name].append({
                    'ref': order.ref,
                    'date': bt.num2date(order.executed.dt),
                    'size': order.executed.size,
                    'price': order.executed.price,
                    'pnl': order.executed.pnl,
                    'direction': "short",
                    'type': order.exectype,
                    'parent': order.parent.ref if order.parent else '-1'
                })               
        
        # If the order is canceled, completed, or rejected, remove it from the order_groups
        if order.status in [order.Canceled, order.Completed, order.Rejected]:
            for idx in range(len(self.order_groups[order.data._name])):
                if order in self.order_groups[order.data._name][idx]:
                    self.order_groups[order.data._name][idx].remove(order)
            
          
        
    # This function is called when an order is canceled
    def cancel_limit_orders(self, crypto):
        for order_group in self.order_groups[crypto._name]:
            for order in order_group:
                self.cancel(order)
        
        self.order_groups[crypto._name] = []
    

    def notify_trade(self, trade: bt.Trade):
 
        if trade.isclosed:
            self.exit[trade.data._name].append(trade)
    
    
   
        
    

        

    

    


        

    



 
              
