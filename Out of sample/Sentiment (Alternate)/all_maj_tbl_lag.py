import datetime
from functools import partial
from tqdm.auto import tqdm
import matplotlib.pyplot as plt

from typing import List, Callable
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score, roc_curve, auc, precision_score, recall_score, confusion_matrix
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, mean_squared_error, mean_absolute_error
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
from itertools import product
from collections import Counter
import vectorbt as vbt
from scipy.optimize import minimize
from pandas.tseries.offsets import DateOffset
import numpy as np
from tabulate import tabulate
import strategy
import backtrader as bt

TICKERS = ["ADA", "BTC", "DOGE", "ETH", "SOL", "XRP"]

class PandasDataWithSignalVolatilityAndSize(bt.feeds.PandasData):
    lines = ('signal', 'volatility', 'position_size', 'upper_barrier', 'lower_barrier', 'vertical_barrier')
    params = (
        ('datetime', None),
        ('open', -1),
        ('high', -1),
        ('low', -1),
        ('close', -1),
        ('volume', -1),
        ('openinterest', -1),
        ('signal', -1),
        ('volatility', -1),
        ('position_size', -1),
        ('upper_barrier', -1),
        ('lower_barrier', -1),
        ('vertical_barrier', -1),
    )

def pandas_data_loader(addr: str, columns: List[str], *transforms: Callable[[pd.DataFrame], pd.DataFrame]) -> pd.DataFrame:
    # Load the data from the CSV file
    df = pd.read_csv(addr, usecols=columns)

    # Apply each transform to the DataFrame
    for transform in transforms:
        df = transform(df)

    return df

def calculate_majority_confidence(labels):
    count = Counter(labels)
    majority_label, majority_count = count.most_common(1)[0]
    total_count = sum(count.values())
    confidence = majority_count / total_count
    return majority_label, confidence

def get_pandas_df(tickers):

    feeds = []

    for ticker in tickers:
        # Transform col to index
        to_index = lambda col, df: df.set_index(col)

        # Load text data
        dir = f"{ticker}/majority_vote_predictions_maj_lag.csv" # @param {"type":"string","placeholder":"./raw/labeled_tweets.csv"}
        columns = ["majority_prediction", "date"]
        text_df = pandas_data_loader(dir, columns, partial(to_index, "date"))
        text_df.rename(columns={"majority_prediction": "impact_label"}, inplace=True)

        # Load price data
        price = f"{ticker}/optimized_labeled_pred_maj_lag.csv" # @param {"type":"string","placeholder":"./raw/price.csv"}
        price = pandas_data_loader(price, ["timestamp", "volatility", "upper_barrier", "lower_barrier", "vertical_barrier"], partial(to_index, "timestamp"))

        price2 = f"{ticker}/{ticker}USDT_1d_2024.csv"
        price2 = pandas_data_loader(price2, ["timestamp", "close", "open", "high", "low"], partial(to_index, "timestamp"))

        price.index = pd.to_datetime(price.index)
        price2.index = pd.to_datetime(price2.index)

        price2 = price2["2024-01-01":]  # Filter to only include data from 2024 onwards
        price = price["2024-01-01":]  # Filter to only include data from 2024 onwards

        # Merge the two price dataframes
        price = price.merge(price2, left_index=True, right_index=True, how='left', suffixes=('', '_2'))

        # Get the mean signal
        # Group by date and apply the function to get majority label and confidence
        majority_data = text_df.groupby(text_df.index)["impact_label"].apply(calculate_majority_confidence)
        majority_df = pd.DataFrame(majority_data.tolist(), index=majority_data.index, columns=["signal", "confidence"])

        mapping = {1: 0, 0: -1, 2: 1}
        majority_df['signal'] = majority_df['signal'].map(mapping)

        # Calculate position size based on confidence
        majority_df["position_size"] = majority_df["confidence"]

        # Rename columns to match the desired output
        impact_majority = majority_df[["signal", "position_size"]]

        scaler = MinMaxScaler(feature_range=(0, 1))
        position_sizes = impact_majority[['position_size']]  # Ensure it's a DataFrame
        impact_majority['position_size'] = scaler.fit_transform(position_sizes)

        # Merge the means with the price data
        impact_majority.index = pd.to_datetime(impact_majority.index)
       
        price = price.merge(impact_majority[['signal', 'position_size']], left_index=True, right_index=True, how='left')

        # Fill NaN values in 'signal' and 'position_size' with 0
        price.volatility.fillna(0, inplace=True)
        price.signal.fillna(0, inplace=True)
        price.position_size.fillna(0, inplace=True)
        price.upper_barrier.fillna(0, inplace=True)
        price.lower_barrier.fillna(0, inplace=True)
        price.vertical_barrier.fillna(0, inplace=True)
        print(price['signal'].value_counts())

        feeds.append(PandasDataWithSignalVolatilityAndSize(dataname=price))
    
    return feeds

feeds = get_pandas_df(TICKERS)

comission = 0.001
cerebro = bt.Cerebro()
cerebro.broker.setcash(100000.0)

for ticker, feed in zip(TICKERS, feeds):
    cerebro.adddata(feed, name=ticker)

cerebro.addstrategy(strategy.ModelStrategy)
# cerebro.addsizer(bt.sizers.PercentSizer)
cerebro.broker.setcommission(commission=comission)
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, compression=1, factor=365, annualize = True, riskfreerate=0.0518)
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")

teststrat = cerebro.run()
analyzers = teststrat[0].analyzers
final_balance = cerebro.broker.getvalue()
initial_balance = 100000.0
strat = teststrat[0]

print("Trades:")

trades = {}

# For each currency pair
for c in strat.trades:
    
    j = 0
    trades[c] = []
    
    # Iterate through trades
    for i in range(len(strat.trades[c])):
        
        # Open trade
        if i%2 == 0:
            trades[c].append(strat.trades[c][i])
            trades[c][-1]['pnl $'] = None
            trades[c][-1]['pair'] = c

        # Close trade
        else:
  
            entry_price = trades[c][j]['price']
            size = trades[c][j]['size']
            exit_price = strat.trades[c][i]['price']
            direction = trades[c][j]['direction']

            if direction == 'long':
                gross_pnl = (exit_price - entry_price) * size
            else:
                gross_pnl = (entry_price - exit_price) * abs(size)
            
            commission_cost = (entry_price + exit_price) * abs(size) * comission

            net_pnl = gross_pnl - commission_cost
        
            trades[c][j]['pnl $'] = net_pnl
            trades[c][j]['pnl %'] = (net_pnl / (entry_price * abs(size))) * 100
            trades[c][j]['exit_price'] = strat.trades[c][i]['price']
            trades[c][j]['exit_date'] = strat.trades[c][i]['date']
            trades[c][j]['duration'] = strat.trades[c][i]['date'] - trades[c][j]['date']
          
            # if strat.trades[c][i]['type'] == 0:
            #     trades[c][j]['order_close'] = 'SIGNAL'

            # elif strat.trades[c][i]['type'] == 3:
            #     trades[c][j]['order_close'] = 'STOP LOSS'

            # else:
            #     trades[c][j]['order_close'] = strat.trades[c][i]['type']

            j += 1

all_trades = []

for c in trades:
    for trade in trades[c]:
        all_trades.append(trade)

all_trades = sorted(all_trades, key=lambda x: x['date'])     
    
# remove 'ref' and 'pnl' columns
for trade in all_trades:
    # trade.pop('ref', None)
    trade.pop('pnl', None)
    trade.pop('type', None)


print(tabulate(all_trades, headers="keys", tablefmt="grid"))

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
print(f"Sharpe Ratio: {sharpe['sharperatio']}")


# Print the maximum drawdown
drawdown = strat.analyzers.drawdown.get_analysis()
print(f"Maximum Drawdown: {drawdown['max']['drawdown']:.2f}%")

# Print the number of trades
count = 0

for trade in all_trades:
    count += 1

print(f"Number of Trades: {count}")

# Print the number of winning trades
winning_trades = [trade for trade in all_trades if trade['pnl $'] is not None and trade['pnl $'] > 0]
print(f"Number of Winning Trades: {len(winning_trades)}")

# Print the number of losing trades
losing_trades = [trade for trade in all_trades if trade['pnl $'] is not None and trade['pnl $'] < 0]
print(f"Number of Losing Trades: {len(losing_trades)}")

# Print the number of open trades
open_trades = [trade for trade in all_trades if trade['pnl $'] is None]
print(f"Number of Open Trades: {len(open_trades)}")

# Print the winning percentage
winning_percentage = (len(winning_trades) / count) * 100 if count > 0 else 0
print(f"Win Rate: {winning_percentage:.2f}%")

# Print number of stop losses
stop_losses = [trade for trade in all_trades if trade.get('order_close') == 'STOP LOSS']
print(f"Number of Stop Loss Signals: {len(stop_losses)}")

# Print number of signal changes
signal_changes = [trade for trade in all_trades if trade.get('order_close') == 'SIGNAL']
print(f"Number of Signal Changes: {len(signal_changes)}")

# Average duration of trades
if count > 0:
    total_duration = sum(
        trade['duration'].days
        for trade in all_trades
        if 'duration' in trade and trade['duration'] is not None
    )
    average_duration = total_duration / count

print(f"Average Duration of Trades: {average_duration:.2f} days")

closed_trades = [trade for trade in all_trades if trade['pnl $'] is not None]
average_pnl = sum(trade['pnl $'] for trade in closed_trades) / len(closed_trades) if closed_trades else 0
print("Aveerage PnL per Trade (USDT):", f"{average_pnl:.2f}")

# Average PnL per winning trade
if len(winning_trades) > 0:
    average_winning_pnl = sum(trade['pnl $'] for trade in winning_trades) / len(winning_trades)
    print(f"Average PnL per Winning Trade (USDT): {average_winning_pnl:.2f}")

# Average PnL per losing trade
if len(losing_trades) > 0:
    average_losing_pnl = sum(trade['pnl $'] for trade in losing_trades) / len(losing_trades)
    print(f"Average PnL per Losing Trade (USDT): {average_losing_pnl:.2f}")

# Highest PnL trade
if all_trades:
    highest_pnl_trade = max(all_trades, key=lambda x: x['pnl $'] if x['pnl $'] is not None else float('-inf'))
    print(f"Highest PnL Trade (USDT): {highest_pnl_trade['pnl $']:.2f}")

# Lowest PnL trade
if all_trades:
    lowest_pnl_trade = min(all_trades, key=lambda x: x['pnl $'] if x['pnl $'] is not None else float('inf'))
    print(f"Lowest PnL Trade (USDT): {lowest_pnl_trade['pnl $']:.2f}")

# Plot the results
cerebro.plot(style='candlestick', plotdist=False, plotmode='single', numfigs=1, volume=False, barupcolor='green', bardowncolor='red', barupfillcolor='green', bardownfillcolor='red')












