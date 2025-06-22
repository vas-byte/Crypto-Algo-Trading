import backtrader as bt
import numpy as np
import pandas as pd
import backtrader.analyzers as btanalyzers
from strategy import Sentiment
from tabulate import tabulate
from multiprocessing import Pool


def run_backtest(tickers, cryptoname, reddit_folders, hours, macd_settings, MA_period, atr_period, obv_period, short, sentiment_positive, sentiment_negative, atr_mean, X_source=True, news_source=True, reddit_source=True):

    # --- Setup Cerebro ---
    cerebro : bt.Cerebro = bt.Cerebro()

    # --- Load XRPUSDT ---
    for ticker in tickers:
        data = pd.read_csv(f'../Data/{ticker}_{hours}.csv', parse_dates=True, index_col='timestamp')
        data_feed = bt.feeds.PandasData(dataname=data)


        # --- Add data feeds to cerebro ---
        cerebro.adddata(data_feed, name=ticker)

    # Add analyzers BEFORE running cerebro

    # Correct Way of calculating Sharpe Ratio - 60 minutes, factor = number of bars in a year, convertrate = True because we are expressing risk free rate per bar, annualize = True to annualize sharpe ratio, riskfreerate = 0.01 is the annual risk free rate
    compression = 60
    factor = 8760

    if hours == '4h':
        compression = 240
        factor = 2190

    cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Minutes, compression=compression, factor=factor, convertrate=True, annualize=True, riskfreerate=0.0209)

    cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addstrategy(Sentiment, can_short=short, cryptoname=cryptoname, reddit_folders=reddit_folders, macd_fast=macd_settings[0], macd_slow=macd_settings[1], macd_signal=macd_settings[2], MAL=MA_period, atr_period=atr_period, obv_period=obv_period, hours=hours, sentiment_positive=sentiment_positive, sentiment_negative=sentiment_negative, atr_mean_period=atr_mean, X_source=X_source, news_source=news_source, reddit_source=reddit_source)

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
                    trades[c][j]['parent'] = strat.trades[c][i]['parent']

                    if strat.trades[c][i]['type'] == 0:
                        trades[c][j]['order_close'] = 'SIGNAL'
                    elif strat.trades[c][i]['type'] == 5:
                        trades[c][j]['order_close'] = 'TRAILING STOP'
                    else:
                        trades[c][j]['order_close'] = strat.trades[c][i]['type']

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


    # Calculate unrealized PnL for open trades
    unrealized_pnl = 0

    for i in range(j, len(all_trades)):
        entry_price = all_trades[i]['price']
        size = all_trades[i]['size']

        exit_price = 0

        if "exit_date" not in all_trades[i]:
        
            if all_trades[i]['pair'] == 'XRPUSDT':
                exit_price = 2.08550000
            elif all_trades[i]['pair'] == 'BTCUSDT':
                exit_price = 86082.50000000
            
            direction = all_trades[i]['direction']

            # priced without commission for exits
            commission_cost = (entry_price) * abs(size) * comission

            if direction == 'long':
                unrealized_pnl += (exit_price - entry_price) * size - commission_cost
            
            else:
                unrealized_pnl += (entry_price - exit_price) * abs(size) - commission_cost

  

    realized_pnl = cerebro.broker.getvalue() - cerebro.broker.startingcash - unrealized_pnl
  
    # Annualized Return
    returns = strat.analyzers.returns.get_analysis()
    
    sharpe = strat.analyzers.sharpe.get_analysis()
  
    drawdown = strat.analyzers.drawdown.get_analysis()
  
    count = 0

    for trade in all_trades:
        count += 1

    winning_trades = [trade for trade in all_trades if trade['pnl $'] is not None and trade['pnl $'] > 0]
   
    losing_trades = [trade for trade in all_trades if trade['pnl $'] is not None and trade['pnl $'] < 0]
 

    open_trades = [trade for trade in all_trades if trade['pnl $'] is None]
   
    winning_percentage = (len(winning_trades) / count) * 100 if count > 0 else 0
   
    stop_losses = [trade for trade in all_trades if trade.get('order_close') == 'STOP LOSS' or trade.get('order_close') == 'TRAILING STOP']
    
    signal_changes = [trade for trade in all_trades if trade.get('order_close') == 'SIGNAL']
   
    if count > 0:
        total_duration = sum(
            trade['duration'].days
            for trade in all_trades
            if 'duration' in trade and trade['duration'] is not None
        )
        average_duration = total_duration / count
    else:
        average_duration = 0


    # Avrage PnL per trade
    if count > 0:
        average_pnl = realized_pnl / count
    else:
        average_pnl = 0
       

    # Average PnL per winning trade
    if len(winning_trades) > 0:
        average_winning_pnl = sum(trade['pnl $'] for trade in winning_trades) / len(winning_trades)
    else:
        average_winning_pnl = 0
       

    # Average PnL per losing trade
    if len(losing_trades) > 0:
        average_losing_pnl = sum(trade['pnl $'] for trade in losing_trades) / len(losing_trades)
    else:
        average_losing_pnl = 0
      

    # Highest PnL trade
    if all_trades:
        highest_pnl_trade = max(all_trades, key=lambda x: x['pnl $'] if x['pnl $'] is not None else float('-inf'))
    else:
        highest_pnl_trade = 0
       

    # Lowest PnL trade
    if all_trades:
        lowest_pnl_trade = min(all_trades, key=lambda x: x['pnl $'] if x['pnl $'] is not None else float('inf'))
    else:
        lowest_pnl_trade = 0

    can_short = 'Yes' if short else 'No'
        
    # Save the trades and performance to a CSV file
    trades_df = pd.DataFrame(all_trades)
    print(trades_df)

    performance_metrics = {
        'Initial Portfolio Value': [cerebro.broker.startingcash],
        'Final Portfolio Value': [cerebro.broker.getvalue()],
        'Total PnL (realized + unrealized)': [cerebro.broker.getvalue() - cerebro.broker.startingcash],
        'Total Realized PnL': [realized_pnl],
        'Unrealized PnL': [unrealized_pnl],
        'Total Return (%)': [(cerebro.broker.getvalue() - cerebro.broker.startingcash) / cerebro.broker.startingcash * 100],
        'Annualized Return (%)': [returns['rnorm100']],
        'Sharpe Ratio': [sharpe['sharperatio']],
        'Maximum Drawdown (%)': [drawdown['max']['drawdown']],
        'Number of Trades': [count],
        'Number of Winning Trades': [len(winning_trades)],
        'Number of Losing Trades': [len(losing_trades)],
        'Number of Open Trades': [len(open_trades)],
        'Win Rate (%)': [winning_percentage],
        'Number of Stop Loss Signals': [len(stop_losses)],
        'Number of Signal Changes': [len(signal_changes)],
        'Average Duration of Trades (days)': [average_duration],
        'Average PnL per Trade (USDT)': [average_pnl if count > 0 else 0],
        'Average PnL per Winning Trade (USDT)': [average_winning_pnl if len(winning_trades) > 0 else 0],
        'Average PnL per Losing Trade (USDT)': [average_losing_pnl if len(losing_trades) > 0 else 0],
        'Highest PnL Trade (USDT)': [highest_pnl_trade['pnl $'] if all_trades else 0],
        'Lowest PnL Trade (USDT)': [lowest_pnl_trade['pnl $'] if all_trades else 0]
    }
    print(performance_metrics)


time = '1h'
tickers = ['ADAUSDT', 'BTCUSDT', 'DOGEUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT']
crypto_names = {
    'ADAUSDT': 'Cardano',
    'BTCUSDT': 'Bitcoin',
    'DOGEUSDT': 'Dogecoin',
    'ETHUSDT': 'Ethereum',
    'SOLUSDT': 'Solana',
    'XMRUSDT': 'Monero',
    'XRPUSDT': 'Ripple'
}
reddit_folders = {
    'ADAUSDT': ['cardano'],
    'BTCUSDT': ['bitcoin', 'bitcoinmarkets', 'btc'],
    'DOGEUSDT': ['dogecoin'],
    'ETHUSDT': ['ethereum', 'ethtrader'],
    'SOLUSDT': ['solana'],
    'XMRUSDT': ['monero', 'xmrtrader'],
    'XRPUSDT': ['ripple', 'xrp']
}


macd_settings = (12, 26, 9)
MA_period = 50
atr = 14
obv_periods = 14
allow_shorting = True
sentiment_thresholds_positive = 0.7
sentiment_thresholds_negative = -0.5
atr_means = 50
reddit_source = False
news_source = False
X_source = True

run_backtest(
    tickers=tickers,
    cryptoname=crypto_names,
    reddit_folders=reddit_folders,
    hours=time,
    macd_settings=macd_settings,
    MA_period=MA_period,
    atr_period=atr,
    obv_period=obv_periods,
    short=allow_shorting,
    sentiment_positive=sentiment_thresholds_positive,
    sentiment_negative=sentiment_thresholds_negative,
    atr_mean=atr_means,
    X_source=X_source,
    news_source=news_source,
    reddit_source=reddit_source
)



