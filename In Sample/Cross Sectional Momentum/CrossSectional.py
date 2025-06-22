import datetime
import backtrader as bt
from tabulate import tabulate
import math
import sys
from scipy.stats import rankdata

class CrossSectionalMomentum(bt.Indicator):
    lines = ('returns',)
    params = (('lookback', 28),)

    def __init__(self):
        self.addminperiod(self.p.lookback + 1)
       

    def next(self):
        lookback = self.p.lookback
        lookback_return = (self.data.close[0] - self.data.close[-lookback]) / self.data.close[-lookback]
        self.lines.returns[0] = lookback_return


class CrossSectional(bt.Strategy):
    params = (
        ('lookback', 1),
        ('stabilization', 40),
        ('holding', 7),
        ('can_short', True),
        ('capped_weights', False),
        ('portfolio', 'market_cap'),
        ('entry_threshold', 1/5),
        ('exit_threshold', 1/5)
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

        self.has_position = False

        self.days = 0
        self.idx = 0

    def start(self):
        self.signal = {data: CrossSectionalMomentum(data, lookback=self.p.lookback) for data in self.datas}

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
        
        # Get the individual returns for each crypto
        raw_returns = [(self.signal[crypto][0], crypto) for crypto in self.datas]

        # Sort the returns in descending order
        raw_returns = sorted(raw_returns, key=lambda x: x[0], reverse=True)

        # Get the top quantile
        top_quantile = int(len(raw_returns) * self.p.entry_threshold)
        long = raw_returns[:top_quantile]

        # Get the bottom quantile
        bottom_quantile = int(len(raw_returns) * self.p.exit_threshold)
        short = raw_returns[-bottom_quantile:]

        # Get the weights for the top quantile
        top_weights = [0] * len(long)

        for i, (ret, crypto) in zip(range(len(top_weights)), long):
         
            if self.p.portfolio == 'volume':
                top_weights[i] = crypto.volume[0] / sum([data.volume[0] for data in self.datas])

                if self.p.capped_weights:
                    top_weights[i] = min(top_weights[i], 0.05)
                    
            elif self.p.portfolio == 'market_cap':
                top_weights[i] = crypto.marketcap[0] / sum([data.marketcap[0] for data in self.datas])

                if self.p.capped_weights:
                    top_weights[i] = min(top_weights[i], 0.05)

            elif self.p.portfolio == 'equal':
                top_weights[i] = 1 / (len(long) + len(short))
        
        bottom_weights = [0] * len(short)

        # Get weights for the bottom quantile
        for i, (ret, crypto) in zip(range(len(top_weights)), short):
    
            if self.p.portfolio == 'volume':
                bottom_weights[i] = crypto.volume[0] / sum([data.volume[0] for data in self.datas])

                if self.p.capped_weights:
                    top_weights[i] = min(top_weights[i], 0.05)

            elif self.p.portfolio == 'market_cap':
                bottom_weights[i] = crypto.marketcap[0] / sum([data.marketcap[0] for data in self.datas])

                if self.p.capped_weights:
                    top_weights[i] = min(top_weights[i], 0.05)

            elif self.p.portfolio == 'equal':
                bottom_weights[i] = 1 / (len(long) + len(short))

        if self.days <= self.p.stabilization:
            self.days += 1
            return
        
        self.holding_period += 1

        if self.holding_period >= self.p.holding:
            
            # Close all positions
            for crypto in self.datas:
                    self.close(data=crypto)
            
            self.holding_period = 0
            self.has_position = False
        
        elif self.has_position:
            return
        
        # Go long the top quantile
        for (ret, crypto), weight in zip(long, top_weights):      

            # Check if the current crypto is not in the trades and exit dictionaries
            # If not, initialize them
            if crypto._name not in self.trades:
                self.trades[crypto._name] = []
            
            if crypto._name not in self.exit:
                self.exit[crypto._name] = []
           
            order = self.buy(data=crypto, size=self.get_size(crypto, weight))
            self.holding_period = 0
            self.has_position = True          
        
        # Go short the bottom quantile
        for (ret, crypto), weight in zip(short, bottom_weights):      

            # Check if the current crypto is not in the trades and exit dictionaries
            # If not, initialize them
            if crypto._name not in self.trades:
                self.trades[crypto._name] = []
            
            if crypto._name not in self.exit:
                self.exit[crypto._name] = []
          
            order = self.sell(data=crypto, size=self.get_size(crypto, weight))
            self.holding_period = 0
            self.has_position = True


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
    
    
   
        
    

        

    

    


        

    



 
              
