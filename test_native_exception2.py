import sys
import os

sys.path.insert(0, os.path.abspath('stock-analysis'))
from trade_visuals import TradeTooltipFactory
import plotly.graph_objects as go
import pandas as pd

factory = TradeTooltipFactory(0, 100)

trade = {
    'entry_date': "not-a-date",
    'exit_date': "also-not-a-date",
    'entry_price': 100.0,
    'exit_price': 110.0,
    'profit': 10.0
}

trace = factory.create_trace(trade)
print(trace is None)
