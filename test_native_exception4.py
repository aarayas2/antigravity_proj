import sys
import os

sys.path.insert(0, os.path.abspath('stock-analysis'))
from trade_visuals import TradeTooltipFactory
import plotly.graph_objects as go
import pandas as pd

factory = TradeTooltipFactory(0, 100)

class MalformedDateStrftime:
    def strftime(self, format):
        raise ValueError("Triggering exception on strftime conversion")
    def __bool__(self):
        return True
    def __str__(self):
        return "2023-01-01"

trade = {
    'entry_date': pd.Timestamp('2023-01-01'),
    'exit_date': MalformedDateStrftime(),
    'entry_price': 100.0,
    'exit_price': 110.0,
    'profit': 10.0
}

trace = factory.create_trace(trade)
print(trace.text)
