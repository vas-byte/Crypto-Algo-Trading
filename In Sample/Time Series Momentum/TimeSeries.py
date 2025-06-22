import datetime
import backtrader as bt
from tabulate import tabulate
import math
import sys
from scipy.stats import rankdata

class TimeSeriesMomentum(bt.Indicator):
    lines = ('returns',)
    params = (('lookback', 28),)

    def __init__(self):
        self.addminperiod(self.p.lookback + 1)
       

    def next(self):
        lookback = self.p.lookback
        lookback_return = (self.data.close[0] - self.data.close[-lookback]) / self.data.close[-lookback]
        self.lines.returns[0] = lookback_return


class TimeSeries(bt.Strategy):
    params = (
        ('lookback', 21),
        ('holding', 7),
        ('can_short', True),
        ('capped_weights', False),
        ('portfolio', 'market_cap'),
        ('stabilization', 40),
        ('entry_threshold', 1/3),
        ('exit_threshold', 2/3)
    )

    def __init__(self):
        self.holding_period = 0
        self.signal = []
        self.returns = []

        self.trades = {}
        self.exit = {}
       
        self.equity = []
        self.max_drawdown = 0
        self.peak_equity = 0

        self.current_dir = ""

        self.days = 0
        self.idx = 0

    def start(self):
        self.signal = {data: TimeSeriesMomentum(data, lookback=self.p.lookback) for data in self.datas}

    def get_size(self, data, weight):
        size = self.broker.getvalue() * weight * 0.9
        commission = self.broker.getcommissioninfo(data).getcommission(data.close[0], 1)
        size = size / (data.close[0] + commission)
        return size

    def next(self):
        
        # Skip the first historical days to stabilize the momentum signal
        if self.days <= self.p.lookback:
            self.days += 1
            return
        
        # Calculate portfolio return
        raw_returns = [self.signal[crypto][0] for crypto in self.datas]

        # Calculate the weights
        weights = [0] * len(self.datas)

        for i in range(len(self.datas)):
            if self.p.portfolio == 'volume':
                weights[i] = self.datas[i].volume[0] / sum([data.volume[0] for data in self.datas])

                if self.p.capped_weights:
                    weights[i] = min(weights[i], 0.05)

            elif self.p.portfolio == 'market_cap':
                weights[i] = self.datas[i].marketcap[0] / sum([data.marketcap[0] for data in self.datas])

                if self.p.capped_weights:
                    weights[i] = min(weights[i], 0.05)

            elif self.p.portfolio == 'equal':
                weights[i] = 1 / len(raw_returns)

        portfolio_return = sum([raw_returns[i] * weights[i] for i in range(len(self.datas))])

        # Add the portfolio return to the returns list
        self.returns.append(portfolio_return)

        # Sort the returns
        self.returns = sorted(self.returns, reverse=True)

        # Calculate the rank of the returns
        ranked = self.returns.index(portfolio_return) + 1
        percentile = ranked / len(self.returns)

        if self.days <= self.p.stabilization:
            self.days += 1
            return
        
        self.holding_period += 1
        
        for crypto, weight in zip(self.datas, weights):      

            # Check if the current crypto is not in the trades and exit dictionaries
            # If not, initialize them
            if crypto._name not in self.trades:
                self.trades[crypto._name] = []
            
            if crypto._name not in self.exit:
                self.exit[crypto._name] = []

            if not self.position:
                
                 # If portfolio return lies within top 1/3, buy the crypto
                if percentile < self.p.entry_threshold:
                    self.buy(data=crypto, size=self.get_size(crypto, weight))
                    self.holding_period = 0
                
                # If portfolio return lies within bottom 1/3, short the crypto
                elif percentile > self.p.exit_threshold:
                    self.sell(data=crypto, size=self.get_size(crypto, weight))
                    self.holding_period = 0

            else:
                if self.holding_period >= self.p.holding:
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
        
    
    def notify_trade(self, trade: bt.Trade):
       
        if trade.isclosed:
            self.exit[trade.data._name].append(trade)

    
    
   
        
    

        

    

    


        

    



 
              
