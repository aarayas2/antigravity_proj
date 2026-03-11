import sys
import os

sys.path.insert(0, os.path.abspath('stock-analysis'))
from trade_visuals import TradeTooltipFactory
import plotly.graph_objects as go

factory = TradeTooltipFactory(0, 100)

class MalformedDate:
    def strftime(self, format):
        # We need this to return a string so that the try block succeeds
        # and doesn't fall into the except block.
        return "2023-01-01"

    def __bool__(self):
        return True

    # But Plotly will try to use this object as an x-coordinate.
    # What happens when Plotly receives this object?

trade = {
    'entry_date': MalformedDate(),
    'exit_date': MalformedDate(),
    'entry_price': 100.0,
    'exit_price': 110.0,
    'profit': 10.0
}

trace = factory.create_trace(trade)
print(trace)
