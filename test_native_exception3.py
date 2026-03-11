import sys
import os

sys.path.insert(0, os.path.abspath('stock-analysis'))
from trade_visuals import TradeTooltipFactory
import plotly.graph_objects as go
import pandas as pd

factory = TradeTooltipFactory(0, 100)

class MalformedDateStr:
    def __str__(self):
        raise Exception("Triggering exception on string conversion")
    def __bool__(self):
        return True

trade = {
    'entry_date': pd.Timestamp('2023-01-01'),
    'exit_date': MalformedDateStr(),
    'entry_price': 100.0,
    'exit_price': 110.0,
    'profit': 10.0
}

trace = factory.create_trace(trade)
print(trace.text)
