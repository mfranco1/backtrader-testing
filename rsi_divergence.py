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

import matplotlib.pyplot as plt
import backtrader as bt

from models import DataMemory, LineMemory
from report import Cerebro

class RSIStrategy(bt.Strategy):
    images_dir = '/home/mfranco/Desktop/trading/backtrader-testing/images/test'

    params = (
        ('memory_size', 5),
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

        self.memory_size = self.params.memory_size
        self.data_memory = DataMemory(self.memory_size)
        self.rsi_memory = LineMemory(self.memory_size)

        self.rsi = rsi = bt.indicators.RSI(self.datas[0])
        #self.sma = bt.indicators.SmoothedMovingAverage(rsi, period=10)

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
        self.log("Today's Open: {}, High: {}, Low: {}, Close: {}, RSI: {}".format(
            self.data_open[0],
            self.data_high[0],
            self.data_low[0],
            self.dataclose[0],
            self.rsi[0],
        ))

        self.data_memory.push(
            open=self.data_open[0],
            high=self.data_high[0],
            low=self.data_low[0],
            close=self.dataclose[0],
        )
        self.rsi_memory.push(self.rsi[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        if (
            self.data_memory.current_size >= self.memory_size
            #and self.rsi_memory.memory[0] > 70
        ):
            #plt.figure()
            rsi_slope = self.get_line_slope(self.rsi_memory, 'RSI')
            price_slope = self.get_line_slope(self.data_memory.closes, 'Price')
            #plt.legend(loc='upper left')
            #plt.title("{} Day Price-RSI Function".format(self.memory_size))
            #plt.savefig(
            #    "{}/{}.png".format(
            #        self.images_dir, self.datas[0].datetime.date(0)
            #    )
            #)
            #plt.close('all')

            # Check if we are in the market
            if not self.position:
                if (
                    self.rsi_memory.memory[0] < 30
                    and rsi_slope > 0
                    and price_slope < 0
                ):
                #if self.rsi[0] < 30:
                    self.log("CREATE BUY ORDER, {}".format(self.dataclose[0]))
                    self.order = self.buy()
            else:
                if (
                    self.rsi_memory.memory[0] > 70
                    and rsi_slope < 0
                    and price_slope > 0
                ):
                #if self.rsi[0] > 70:
                    self.log("CREATE SELL ORDER, {}".format(self.dataclose[0]))
                    self.order = self.sell()
                    self.total_trades += 1

    def get_line_slope(self, memory, indicator=''):
        x, y, yspline, yderivative = memory.get_interpolation()
        slope, intercept = memory.get_linear_trend(yspline)
        ytrend = intercept + slope * x
        #plt.plot(x, yspline, label="{} Spline".format(indicator))
        #plt.plot(x, yderivative, label="{} Derivative".format(indicator))
        #plt.plot(x, ytrend, label="{} Tendency".format(indicator))
        return slope

    def stop(self):
        #print("Total Gross Profit: {}, Losses: {}".format(
        #    self.gross_profits, self.gross_losses
        #))
        #print("Total Trades Closed: {}".format(self.total_trades))
        #print("Percent Profitable: {}".format(self.percent_profitable))
        #print("Profit Factor: {}".format(self.profit_factor))
        super().stop()


if __name__ == '__main__':
    cerebro = bt.Cerebro()
    #cerebro = Cerebro()
    #cerebro.optstrategy(RSIStrategy, memory_size=range(5,51))
    cerebro.addstrategy(RSIStrategy)

    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, 'YHF-BTC-USD.csv')

    data = bt.feeds.YahooFinanceCSVData(
        dataname=datapath,
        fromdate=datetime.datetime(2010, 1, 1),
        todate=datetime.datetime(2019, 12, 31),
        reverse=False)

    cerebro.adddata(data)
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.0)
    starting_cash = cerebro.broker.getvalue()
    print("Starting Portfolio Value: {}".format(starting_cash))
    #results = cerebro.run(optreturn=False)
    cerebro.run()
    headers = ["PERIODS"]
    profits = ["GROSS PROFITS"]
    losses = ["GROSS LOSSES"]
    trades = ["TOTAL TRADES CLOSED"]
    percent_profitable = ["PERCENT PROFITABLE"]
    profit_factor = ["PROFIT FACTOR"]
    max_drawdown = ["MAX DRAWDOWN"]
    max_profit = ["MAX PROFIT"]
    #for strat in results:
    #    strat = strat[0]
    #    headers.append("PERIOD {}".format(strat.params.memory_size))
    #    profits.append(strat.gross_profits)
    #    losses.append(strat.gross_losses)
    #    trades.append(strat.total_trades)
    #    percent_profitable.append(strat.percent_profitable)
    #    profit_factor.append(strat.profit_factor)
    #    max_drawdown.append(strat.max_drawdown)
    #    max_profit.append(strat.max_profit)
    #with open('./results_rsi_divergence.csv', 'w') as csvfile:
    #    writer = csv.writer(csvfile, delimiter=",")
    #    writer.writerow(headers)
    #    writer.writerow(profits)
    #    writer.writerow(losses)
    #    writer.writerow(trades)
    #    writer.writerow(percent_profitable)
    #    writer.writerow(profit_factor)
    #    writer.writerow(max_drawdown)
    #    writer.writerow(max_profit)
    final_cash = cerebro.broker.getvalue()
    net_profit = final_cash - starting_cash
    print("Final Portfolio Value: {}".format(final_cash))
    print("Net Profit: {}".format(net_profit))
    cerebro.plot()
    #cerebro.plot('./rsi_5_day_divergence_plot.png')
    #cerebro.report(
        #'./',
        #infile='YHF-BTC-USD.csv',
        #user='TradingMachine',
        #memo='5 Day RSI Divergence'
    #)
