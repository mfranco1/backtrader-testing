import numpy as np
from scipy import interpolate, stats

class LineMemory:
    def __init__(self, memory_size):
        self.memory_size = memory_size
        self.memory = []
        self.highest = 0
        self.lowest = 0

    def push(self, item):
        if len(self.memory) >= self.memory_size:
            self.pop()
        self.memory.append(item)
        self.update_highest_lowest()
        return item

    def pop(self, index=0):
        if self.memory:
            result = self.memory.pop(index)
            self.update_highest_lowest()
            return result
        return 0

    def update_highest(self):
        if len(self.memory) > 1:
            self.highest = max(self.memory[:-1]) # exclude current period
        else:
            self.highest = 0

    def update_lowest(self):
        if len(self.memory) > 1:
            self.lowest = min(self.memory[:-1]) # exclude current period
        else:
            self.lowest = 0

    def update_highest_lowest(self):
        self.update_highest()
        self.update_lowest()

    def get_interpolation(self):
        x = np.arange(0, len(self.memory))
        y = self.memory

        tck = interpolate.splrep(x, y, s=0)
        ynew = interpolate.splev(x, tck, der=0)
        yder = interpolate.splev(x, tck, der=1)

        return x, y, ynew, yder

    def get_linear_trend(self, memory):
        x = np.arange(0, len(memory))
        y = memory

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        return slope, intercept


class DataMemory:
    def __init__(self, size):
        self.size = size
        self.current_size = 0
        self.memory = {
            "open": LineMemory(size),
            "high": LineMemory(size),
            "low": LineMemory(size),
            "close": LineMemory(size),
        }
        self.opens = self.memory["open"]
        self.highs = self.memory["high"]
        self.lows = self.memory["low"]
        self.closes = self.memory["close"]

    def push(self, open, high, low, close):
        if self.current_size >= self.size:
            self.pop()
        return self.push_all(open=open, high=high, low=low, close=close)

    def pop(self, index=0):
        open = self.opens.pop(index)
        high = self.highs.pop(index)
        low = self.lows.pop(index)
        close = self.closes.pop(index)
        if self.current_size > 0:
            self.current_size -= 1
        return open, high, low, close

    def push_all(self, open, high, low, close):
        self.opens.push(open)
        self.highs.push(high)
        self.lows.push(low)
        self.closes.push(close)
        self.current_size += 1
        return open, high, low, close

