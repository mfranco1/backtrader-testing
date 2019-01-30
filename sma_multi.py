from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals
)

import csv
import datetime
import os.path
import sys
import time

import backtrader as bt


class SMAStrategy(bt.Strategy):
    params = (
        ('sma_period', (10, 20)),
    )

    def log(self, txt, dt=None, debug=False):
        if debug:
            dt = dt or self.datas[0].datetime.date(0)
            print("{}, {}".format(dt.isoformat(), txt))

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None

        self.wins = 0
        self.gross_profits = 0
        self.gross_losses = 0
        self.max_profit = 0
        self.max_drawdown = 0
        self.total_trades = 0
        self.percent_profitable = 0
        self.profit_factor = 0

        self.sma_short = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.sma_period[0]
        )
        self.sma_long = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.sma_period[1]
        )
        #self.sma = bt.indicators.SimpleMovingAverage(
        #    self.datas[0], period=20
        #)
        #self.sma = bt.indicators.SimpleMovingAverage(
        #    self.datas[0], period=30
        #)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    "BUY EXECUTED, Price: {}, Cost: {}, Comm: {}".format(
                        order.executed.price,
                        order.executed.value,
                        order.executed.comm,
                    )
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log(
                    "SELL EXECUTED, Price: {}, Cost: {}, Comm: {}".format(
                        order.executed.price,
                        order.executed.value,
                        order.executed.comm,
                    )
                )

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        if trade.pnl > 0:
            self.wins += 1
            self.gross_profits += trade.pnl
            if trade.pnl > self.max_profit:
                self.max_profit = trade.pnl
        else:
            self.gross_losses -= trade.pnl
            if trade.pnl < self.max_drawdown:
                self.max_drawdown = trade.pnl

        if self.total_trades:
            self.percent_profitable = self.wins / self.total_trades
        if self.gross_losses != 0:
            self.profit_factor = self.gross_profits / self.gross_losses
        else:
            self.profit_factor = self.gross_profits / 1

        self.log("ORDER PROFIT, GROSS: {}, NET: {}".format(
                trade.pnl, trade.pnlcomm
            )
        )

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log("Today's Open: {}, High: {}, Low: {}, Close: {}".format(
            self.data_open[0],
            self.data_high[0],
            self.data_low[0],
            self.dataclose[0],
        ))

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            #if self.dataclose[0] > self.sma[0]:
            if self.sma_short[0] > self.sma_long[0]:
                self.log("CREATE BUY ORDER, {}".format(self.dataclose[0]))
                self.order = self.buy()
        else:
            #if self.dataclose[0] < self.sma[0]:
            if self.sma_short[0] < self.sma_long[0]:
                self.log("CREATE SELL ORDER, {}".format(self.dataclose[0]))
                self.order = self.sell()
                self.total_trades += 1

    def stop(self):
        #print("PERIOD {}".format(self.params.sma_period))
        #print("Total Gross Profit: {}, Losses: {}".format(
        #    self.gross_profits, self.gross_losses
        #))
        #print("Total Trades Closed: {}".format(self.total_trades))
        #print("Percent Profitable: {}".format(self.percent_profitable))
        #print("Profit Factor: {}".format(self.profit_factor))
        #print("")
        super().stop()


if __name__ == '__main__':
    images_dir = '/home/mfranco/Desktop/trading/test_proj1/images'
    periods = []
    for i in range(5, 100, 5):
        for j in range(i + 5, 105, 5):
            periods.append((i, j))
    cerebro = bt.Cerebro()
    cerebro.optstrategy(SMAStrategy, sma_period=periods)

    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, 'YHF-BTC-USD.csv')

    data = bt.feeds.YahooFinanceCSVData(
        dataname=datapath,
        fromdate=datetime.datetime(2012, 1, 1),
        todate=datetime.datetime(2019, 12, 31),
        reverse=False)

    cerebro.adddata(data)
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.0)
    starting_cash = cerebro.broker.getvalue()
    print("Starting Portfolio Value: {}".format(starting_cash))
    start_time = time.time()
    results = cerebro.run(optreturn=False)
    elapsed_time = time.time() - start_time
    elapsed_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    total_runs = ["TOTAL CASES"]
    headers = ["PERIODS"]
    profits = ["GROSS PROFITS"]
    losses = ["GROSS LOSSES"]
    trades = ["TOTAL TRADES CLOSED"]
    percent_profitable = ["PERCENT PROFITABLE"]
    profit_factor = ["PROFIT FACTOR"]
    max_drawdown = ["MAX DRAWDOWN"]
    max_profit = ["MAX PROFIT"]
    runtime = ["RUN TIME"]
    for strat in results:
        strat = strat[0]
        total_runs.append(str(len(periods)))
        headers.append("PERIOD {}".format(strat.params.sma_period))
        profits.append(strat.gross_profits)
        losses.append(strat.gross_losses)
        trades.append(strat.total_trades)
        percent_profitable.append(strat.percent_profitable)
        profit_factor.append(strat.profit_factor)
        max_drawdown.append(strat.max_drawdown)
        max_profit.append(strat.max_profit)
        runtime.append(elapsed_time)
    with open('./results.csv', 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=",")
            writer.writerow(total_runs)
            writer.writerow(headers)
            writer.writerow(profits)
            writer.writerow(losses)
            writer.writerow(trades)
            writer.writerow(percent_profitable)
            writer.writerow(profit_factor)
            writer.writerow(max_drawdown)
            writer.writerow(max_profit)
            writer.writerow(runtime)
    final_cash = cerebro.broker.getvalue()
    net_profit = final_cash - starting_cash
    print("Final Portfolio Value: {}".format(final_cash))
    print("Net Profit: {}".format(net_profit))
    #figures = cerebro.plot()
    #for figure, period in zip(figures, periods):
    #    figure[0].savefig("{}/sma-{}period.png".format(images_dir, period))

