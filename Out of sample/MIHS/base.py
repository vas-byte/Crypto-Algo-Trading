import backtrader as bt
import pandas as pd
import backtrader.analyzers as btanalyzers
from MIHS import MIHS
from tabulate import tabulate

# --- Setup Cerebro ---
cerebro : bt.Cerebro = bt.Cerebro()


# --- Load Data ---
data_ada = pd.read_csv('../Data/ADAUSDT_1d.csv', parse_dates=True, index_col='timestamp')
data_feed_ada = bt.feeds.PandasData(dataname=data_ada)

data_btc = pd.read_csv('../Data/BTCUSDT_1d.csv', parse_dates=True, index_col='timestamp')
data_feed_btc = bt.feeds.PandasData(dataname=data_btc)

data_doge = pd.read_csv('../Data/DOGEUSDT_1d.csv', parse_dates=True, index_col='timestamp')
data_feed_doge = bt.feeds.PandasData(dataname=data_doge)

data_eth = pd.read_csv('../Data/ETHUSDT_1d.csv', parse_dates=True, index_col='timestamp')
data_feed_eth = bt.feeds.PandasData(dataname=data_eth)

data_sol = pd.read_csv('../Data/SOLUSDT_1d.csv', parse_dates=True, index_col='timestamp')
data_feed_sol = bt.feeds.PandasData(dataname=data_sol)

data_xrp = pd.read_csv('../Data/XRPUSDT_1d.csv', parse_dates=True, index_col='timestamp')
data_feed_xrp = bt.feeds.PandasData(dataname=data_xrp)

# --- Add data feeds to cerebro ---
cerebro.adddata(data_feed_ada, name='ADAUSDT')
cerebro.adddata(data_feed_btc, name='BTCUSDT')
cerebro.adddata(data_feed_doge, name='DOGEUSDT')
cerebro.adddata(data_feed_eth, name='ETHUSDT')
cerebro.adddata(data_feed_sol, name='SOLUSDT')
cerebro.adddata(data_feed_xrp, name='XRPUSDT')

# Add analyzers BEFORE running cerebro
cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, compression=1, factor=365, annualize=True, riskfreerate=0.0518)
cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')
cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")

double_down = False

cerebro.addstrategy(MIHS, can_short=False, double_down=double_down, signal_period=7)

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
        
        # If double down is allowed
        if double_down:
            
            # Open trade
            if strat.trades[c][i]['pnl'] == 0:
                trades[c].append(strat.trades[c][i])
                trades[c][-1]['pnl $'] = None
                trades[c][-1]['pair'] = c
               
            # Close trade
            else:

                remaining_size = strat.trades[c][i]['size']

                # If the trade is initiated by self.close
                if strat.trades[c][i]['parent'] == '-1':
                    
                    # Populate closing trades
                    while j < min(i,len(trades[c])) and remaining_size != 0:

                        # if the trade closed by stop loss, skip it
                        if trades[c][j]['pnl $'] != None:
                            j += 1
                            continue

                        entry_price = trades[c][j]['price']
                        size = trades[c][j]['size']
                        exit_price = strat.trades[c][i]['price']
                        direction = trades[c][j]['direction']
                        remaining_size += size

                        if direction == 'long':
                            gross_pnl = (exit_price - entry_price) * size
                        else:
                            gross_pnl = (entry_price - exit_price) * abs(size)
                        
                        commission_cost = (entry_price + exit_price) * abs(size) * comission

                        net_pnl = gross_pnl - commission_cost
                    
                        trades[c][j]['pnl $'] = net_pnl
                        trades[c][j]['pnl %'] = (trades[c][j]['pnl $'] / (entry_price * abs(size))) * 100
                        trades[c][j]['exit_price'] = strat.trades[c][i]['price']
                        trades[c][j]['exit_date'] = strat.trades[c][i]['date']
                        trades[c][j]['duration'] = strat.trades[c][i]['date'] - trades[c][j]['date']
                        trades[c][j]['parent'] = strat.trades[c][i]['parent']
                        trades[c][j]['order_close'] = 'SIGNAL'
                     
                        j += 1
                
                # If trade is closd by stop loss
                else:

                    # Find the parent trade and populate it
                    for k in range(len(trades[c])):
                        if trades[c][k]['ref'] == strat.trades[c][i]['parent']:

                            entry_price = trades[c][k]['price']
                            size = trades[c][k]['size']
                            exit_price = strat.trades[c][i]['price']
                            direction = trades[c][k]['direction']
                            remaining_size += size

                            if direction == 'long':
                                gross_pnl = (exit_price - entry_price) * size
                            else:
                                gross_pnl = (entry_price - exit_price) * abs(size)
                            
                            commission_cost = (entry_price + exit_price) * abs(size) * comission

                            net_pnl = gross_pnl - commission_cost
                        
                            trades[c][k]['pnl $'] = net_pnl
                            trades[c][k]['pnl %'] = (trades[c][k]['pnl $'] / (entry_price * abs(size))) * 100
                            trades[c][k]['exit_price'] = strat.trades[c][i]['price']
                            trades[c][k]['exit_date'] = strat.trades[c][i]['date']
                            trades[c][k]['duration'] = strat.trades[c][i]['date'] - trades[c][k]['date']
                            trades[c][k]['parent'] = strat.trades[c][i]['parent']
                            trades[c][k]['order_close'] = 'STOP LOSS'
                            break
                        
        # Otherwise, if double down is not allowed
        else:

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
                elif strat.trades[c][i]['type'] == 3:
                    trades[c][j]['order_close'] = 'STOP LOSS'
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

print(tabulate(all_trades, headers="keys", tablefmt="grid"))

# Print initial portfolio value
print(f"Initial Portfolio Value: {cerebro.broker.startingcash:.2f}")

# Print the new portfolio value
print(f"Final Portfolio Value: {cerebro.broker.getvalue():.2f}")
print(f"Final Cash: {cerebro.broker.getcash():.2f}")

# Print the total PnL
print(f"Total PnL (realized + unrealized): {cerebro.broker.getvalue() - cerebro.broker.startingcash:.2f}")

# Print the trade profit/loss
realized_pnl = cerebro.broker.getvalue() - cerebro.broker.startingcash - unrealized_pnl
print(f"Total Realized PnL: {realized_pnl:.2f}")

# Print the unrealized PnL
print(f"Unrealized PnL: {unrealized_pnl:.2f}")

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

# Avrage PnL per trade
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


