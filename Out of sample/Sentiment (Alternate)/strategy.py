import backtrader as bt

class ModelStrategy(bt.Strategy):
    params = (
        ('vertical_barrier', 30),
        ('max_days_open', 30),
        ('base_position_size', 1),
    )

    def __init__(self):
        self.orders = {}
        self.trades = {}
        self.exits = {}
        self.entry_prices = {}
        self.tp_prices = {}
        self.sl_prices = {}
        self.entry_bars = {}

        for data in self.datas:
            name = data._name
            self.orders[name] = None
            self.trades[name] = []
            self.exits[name] = []
            self.entry_prices[name] = None
            self.tp_prices[name] = None
            self.sl_prices[name] = None
            self.entry_bars[name] = None

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} - {txt}')

    def next(self):
        for data in self.datas:
            name = data._name
            dataclose = data.close[0]
            signal = data.signal[0]
            volatility = data.volatility[0]
            position_size = data.position_size[0]
            upper_barrier = data.upper_barrier[0]
            lower_barrier = data.lower_barrier[0]
            vertical_barrier = data.vertical_barrier[0]

            pos = self.getposition(data)

            if not pos:
                cash = self.broker.get_cash()
                value = cash * position_size
                units = value / dataclose

                if signal > 0:
                    data.entry_price = dataclose
                    self.tp_prices[name] = upper_barrier or dataclose * (1 + volatility)
                    self.sl_prices[name] = lower_barrier or dataclose * (1 - volatility)
                    self.entry_bars[name] = len(self)
                    self.orders[name] = self.buy(data=data, size=units)
                    self.log(f'{name} BUY {units:.2f} @ {dataclose:.2f}')

                elif signal < 0:
                    data.entry_price = dataclose
                    self.tp_prices[name] = lower_barrier or dataclose * (1 - volatility)
                    self.sl_prices[name] = upper_barrier or dataclose * (1 + volatility)
                    self.entry_bars[name] = len(self)
                    self.orders[name] = self.sell(data=data, size=units)
                    self.log(f'{name} SELL {units:.2f} @ {dataclose:.2f}')

            else:
                days_open = len(self) - self.entry_bars[name]

                if dataclose >= self.tp_prices[name]:
                    self.close(data=data)
                    self.log(f'{name} TP hit @ {dataclose:.2f}')
                elif dataclose <= self.sl_prices[name]:
                    self.close(data=data)
                    self.log(f'{name} SL hit @ {dataclose:.2f}')
                elif days_open >= self.params.max_days_open:
                    self.log(f'{name} max days open reached')
                    self.close(data=data)
                elif days_open >= vertical_barrier:
                    self.log(f'{name} vertical barrier hit')
                    self.close(data=data)

    def notify_order(self, order: bt.Order):
        data = order.data
        name = data._name
        if order.status in [order.Completed]:
            direction = "long" if order.isbuy() else "short"

            self.trades[name].append({
                'ref': order.ref,
                'date': bt.num2date(order.executed.dt),
                'size': order.executed.size,
                'price': order.executed.price,
                'pnl': order.executed.pnl,
                'direction': direction,
            })

            self.orders[name] = None  # Clear the order slot

        elif order.status in [order.Canceled, order.Rejected]:
            self.orders[name] = None

    def notify_trade(self, trade: bt.Trade):
        name = trade.data._name
        if trade.isclosed:
            self.exits[name].append(trade)
