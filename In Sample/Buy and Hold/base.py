import backtrader as bt
import numpy as np
import pandas as pd
import backtrader.analyzers as btanalyzers
from tabulate import tabulate

class BuyAndHold(bt.Strategy): 
    def next(self):

        # Buy all the available cash
        if not self.position:
            size = (self.broker.get_cash()) / (self.data.close[0] + self.data.close[0] * 0.001) / len(self.datas)  # Divide by number of data feeds to spread the investment
            self.buy(size=size)

# --- Setup Cerebro ---
cerebro : bt.Cerebro = bt.Cerebro()

# --- Load Data ---
data = pd.read_csv('../Data/ADAUSDT_1d.csv', parse_dates=True, index_col='timestamp')
data_feed = bt.feeds.PandasData(dataname=data)

data2 = pd.read_csv('../Data/BTCUSDT_1d.csv', parse_dates=True, index_col='timestamp')
data_feed2 = bt.feeds.PandasData(dataname=data2)

data3 = pd.read_csv('../Data/DOGEUSDT_1d.csv', parse_dates=True, index_col='timestamp')
data_feed3 = bt.feeds.PandasData(dataname=data3)

data4 = pd.read_csv('../Data/ETHUSDT_1d.csv', parse_dates=True, index_col='timestamp')
data_feed4 = bt.feeds.PandasData(dataname=data4)

data5 = pd.read_csv('../Data/SOLUSDT_1d.csv', parse_dates=True, index_col='timestamp')
data_feed5 = bt.feeds.PandasData(dataname=data5)

data6 = pd.read_csv('../Data/XMRUSDT_1d.csv', parse_dates=True, index_col='timestamp')
data_feed6 = bt.feeds.PandasData(dataname=data6)

data7 = pd.read_csv('../Data/XRPUSDT_1d.csv', parse_dates=True, index_col='timestamp')
data_feed7 = bt.feeds.PandasData(dataname=data7)

# --- Add data feeds to cerebro ---
cerebro.adddata(data_feed, name='DOGEUSDT')
cerebro.adddata(data_feed2, name='BTCUSDT')
cerebro.adddata(data_feed3, name='ADAUSDT')
cerebro.adddata(data_feed4, name='ETHUSDT')
cerebro.adddata(data_feed5, name='SOLUSDT')
cerebro.adddata(data_feed6, name='XMRUSDT')
cerebro.adddata(data_feed7, name='XRPUSDT')

# Add analyzers BEFORE running cerebro

# Correct Way of calculating Sharpe Ratio - 60 minutes, factor = number of bars in a year, convertrate = True because we are expressing risk free rate per bar, annualize = True to annualize sharpe ratio, riskfreerate = 0.01 is the annual risk free rate
cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, compression=1, factor=365, annualize=True, riskfreerate=0.0209)

cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')
cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")

cerebro.addstrategy(BuyAndHold)

# Optional: set initial capital
cerebro.broker.set_cash(100000)

# Optional: set commission'
comission = 0.001
cerebro.broker.setcommission(commission=comission)  # 0.1% commission

# Optional: set slippage
# slippage = 0.01
# cerebro.broker.set_slippage_perc(perc=slippage)  # percentage slippage

# --- 3. Run backtest ---
# Run and get strategy instance
results = cerebro.run()
strat = results[0]



# Print initial portfolio value
print(f"Initial Portfolio Value: {cerebro.broker.startingcash:.2f}")

# Print the new portfolio value
print(f"Final Portfolio Value: {cerebro.broker.getvalue():.2f}")
print(f"Final Cash: {cerebro.broker.getcash():.2f}")

# Print the total PnL
print(f"Total PnL (realized + unrealized): {cerebro.broker.getvalue() - cerebro.broker.startingcash:.2f}")

# Total Return
print(f"Total Return: {((cerebro.broker.getvalue() - cerebro.broker.startingcash) / cerebro.broker.startingcash) * 100:.2f}%")

# Annualized Return
returns = strat.analyzers.returns.get_analysis()
print(f"Annualized Return: {returns['rnorm100']:.2f}%")

# Print the Sharpe Ratio
sharpe = strat.analyzers.sharpe.get_analysis()
print(f"Sharpe Ratio: {sharpe['sharperatio']:.2f}")

# Print the maximum drawdown
drawdown = strat.analyzers.drawdown.get_analysis()
print(f"Maximum Drawdown: {drawdown['max']['drawdown']:.2f}%")

# Plot the results
cerebro.plot(style='candlestick', plotdist=False, plotmode='single', numfigs=1, volume=False, barupcolor='green', bardowncolor='red', barupfillcolor='green', bardownfillcolor='red')

