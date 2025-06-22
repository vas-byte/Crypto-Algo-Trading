import datetime
import backtrader as bt
from tabulate import tabulate
import math
import sys

class MIHS(bt.Strategy):
    params = (
        ('double_down', False),
        ('can_short', False),
        ('signal_period', 7),
    )

    def __init__(self):
        self.sar = {}
        self.ema9 = {}
        self.ema20 = {}
        self.ema_rsi = {}
        self.rsi = {}
        
        self.trades = {}
        self.exit = {}
       
        self.equity = []
        self.max_drawdown = 0
        self.peak_equity = 0

        self.current_dir = ""

        self.order_groups = {}

        self.idx = 0
        self.days = 0

    def start(self):
        for data in self.datas:

            # Compute the SAR indicator
            self.sar[data] = bt.talib.SAR(self.data.high, self.data.low, acceleration=0.02, maximum=0.2)
            
            # Compute the EMA indicators
            self.ema9[data] = bt.talib.EMA(data.close, timeperiod=9)
            self.ema20[data] = bt.talib.EMA(data.close, timeperiod=20)
            self.ema_rsi[data] = bt.talib.EMA(bt.talib.RSI(data.close, timeperiod=14), timeperiod=self.p.signal_period)

            # Compute the RSI indicator
            self.rsi[data] = bt.talib.RSI(data.close, timeperiod=14)
           
        for stream in self.datas:
            self.order_groups[stream._name] = []
    
    def get_size(self, crypto):
        # get closing price + commission
        closing_price = crypto.close[0] + crypto.close[0] * 0.001


        equity = 10000 

        if self.broker.getvalue() < 10000:
            equity = self.broker.getvalue() * 0.15
        
        # calculate the size of the order
        size = equity / closing_price

        return size


    def next(self):

        self.days += 1
        
        for crypto in self.datas:
        
            # Skip the first bars until indicators are ready
            if self.days <= 31:
                return
        
            # Check if the current crypto is not in the trades and exit dictionaries
            # If not, initialize them
            if crypto._name not in self.trades:
                self.trades[crypto._name] = []
            
            if crypto._name not in self.exit:
                self.exit[crypto._name] = []


            # Buy Signal
            rsi_buy = ((self.ema_rsi[crypto][0] >= 40) & (self.ema_rsi[crypto][0] <= 60) & (self.rsi[crypto][0] < 45) & (self.rsi[crypto][-1] < self.rsi[crypto][0]))
            psar_buy = ((self.ema_rsi[crypto][0] < 40) & (self.sar[crypto][0] <= crypto.close[0]) & (self.sar[crypto][-1] >= self.sar[crypto][0]))
            ema_buy = ((self.ema_rsi[crypto][0] > 60) & (self.ema9[crypto][0] > self.ema20[crypto][0]))
            can_buy = rsi_buy or psar_buy or ema_buy

            # Sell Signal
            rsi_sell = ((self.ema_rsi[crypto][0] >= 40) & (self.ema_rsi[crypto][0] <= 60) & (self.rsi[crypto][0] > 55) & (self.rsi[crypto][-1] > self.rsi[crypto][0]))
            psar_sell = ((self.ema_rsi[crypto][0] < 40) & (self.sar[crypto][0] > crypto.close[0]) & (self.sar[crypto][-1] < self.sar[crypto][0]))
            ema_sell = ((self.ema_rsi[crypto][0] > 60) & (self.ema9[crypto][0] < self.ema20[crypto][0]))
            can_sell = rsi_sell or psar_sell or ema_sell

            # Buy
            if can_buy:
            
                if self.getposition(crypto).size < 0:
                    self.close(data=crypto)
                  
                if self.p.double_down:
                    size = self.get_size(crypto)
                    order = self.buy(data=crypto, size=size)
                
                elif self.getposition(crypto).size <= 0:
                    size = self.get_size(crypto)
                    order = self.buy(data=crypto, size=size)
                   
                    
            # Sell
            elif can_sell:


                if self.getposition(crypto).size > 0:
                    # If the current position is long, close the position
                    self.close(data=crypto)
                    
    
                if self.p.double_down and self.p.can_short:
                    
                    size = self.get_size(crypto)

                    # Place short order
                    order = self.sell(data=crypto, size=size)

                    
                elif self.getposition(crypto).size >= 0 and self.p.can_short:
                    size = self.get_size(crypto)
                    order = self.sell(data=crypto, size=size)
                  
                    

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
        
    

    def notify_trade(self, trade: bt.Trade):
 
        if trade.isclosed:
            self.exit[trade.data._name].append(trade)
    
    
   
        
    

        

    

    


        

    



 
              
