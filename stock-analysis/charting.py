"""
Charting Module
===============

This module provides functions for generating the Plotly Dash charts used
to visualize stock prices, technical indicators, and trade executions. 
It uses the Factory pattern (`TradeTooltipFactory`) for drawing complex 
trade window visualizations.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Any

from strategy import STRATEGIES
from trade_visuals import TradeTooltipFactory

class MockFig:
    """
    Dummy wrapper to maintain compatibility between go.Figure and
    make_subplots when adding traces to rows/cols.
    """
    def __init__(self, fig):
        self.fig = fig
        
    def add_trace(self, trace, row=None, col=None):
        self.fig.add_trace(trace)
        
    def update_layout(self, **kwargs):
        self.fig.update_layout(**kwargs)
        
    def add_vrect(self, **kwargs):
        self.fig.add_vrect(**kwargs)
        
    def add_hline(self, **kwargs):
        self.fig.add_hline(**kwargs)

def create_strategy_chart(df_with_signals: pd.DataFrame, strategy: str, metrics: Dict[str, Any]) -> go.Figure:
    """
    Generates a full Plotly Figure for a given strategy.

    Args:
        df_with_signals: The DataFrame containing price data and strategy signals.
        strategy: The name of the strategy to plot.
        metrics: The calculated metrics dictionary containing trades history.

    Returns:
        go.Figure: The fully configured Plotly chart.
    """
    needs_subplots = False
    if strategy in STRATEGIES:
        needs_subplots = STRATEGIES[strategy]["needs_subplots"]()

    if needs_subplots:
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.7, 0.3],
            vertical_spacing=0.08
        )
        main_row = 1
        sub_row = 2
    else:
        fig = go.Figure()
        fig_wrapper = MockFig(fig)
        fig = fig_wrapper.fig  # Overwrite for simplicity in charting later
        main_row = None
        sub_row = None

    # Draw trade duration windows with tooltips (must be drawn before candlesticks to appear underneath)
    trades_history = metrics.get("Trades History", [])
    if trades_history and not df_with_signals.empty:
        y_min = df_with_signals['Low'].min() * 0.95
        y_max = df_with_signals['High'].max() * 1.05
        tooltip_factory = TradeTooltipFactory(y_min=y_min, y_max=y_max)
        
        for trade in trades_history:
            trade_trace = tooltip_factory.create_trace(trade)
            if trade_trace:
                if main_row:
                    fig.add_trace(trade_trace, row=main_row, col=1)
                else:
                    fig.add_trace(trade_trace)

    # Main Candlestick Chart
    candlestick = go.Candlestick(
        x=df_with_signals.index,
        open=df_with_signals['Open'],
        high=df_with_signals['High'],
        low=df_with_signals['Low'],
        close=df_with_signals['Close'],
        name="Price"
    )
    if main_row:
        fig.add_trace(candlestick, row=main_row, col=1)
    else:
        fig.add_trace(candlestick)

    # Add Strategy Traces
    if strategy in STRATEGIES:
        STRATEGIES[strategy]["add_traces"](fig, df_with_signals, main_row, sub_row)

    # Plot Buy/Sell signals on main chart
    buy_signals = pd.DataFrame()
    sell_signals = pd.DataFrame()
    if strategy in STRATEGIES:
        buy_signals, sell_signals = STRATEGIES[strategy]["get_signals"](df_with_signals)
    
    if not buy_signals.empty:
        trace = go.Scatter(
            x=buy_signals.index, y=buy_signals['Low'] * 0.98,
            mode='markers', marker=dict(symbol='triangle-up', size=12, color='green'),
            name='Buy Signal'
        )
        if main_row:
            fig.add_trace(trace, row=main_row, col=1)
        else:
            fig.add_trace(trace)
        
    if not sell_signals.empty:
        trace = go.Scatter(
            x=sell_signals.index, y=sell_signals['High'] * 1.02,
            mode='markers', marker=dict(symbol='triangle-down', size=12, color='red'),
            name='Sell Signal'
        )
        if main_row:
            fig.add_trace(trace, row=main_row, col=1)
        else:
            fig.add_trace(trace)

    # Layout updates
    fig.update_layout(
        height=700, template="plotly_dark",
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=30, b=0)
    )
    if main_row:
         # Ensure rangeslider off for all subplots
         fig.update_xaxes(rangeslider_visible=False)

    return fig
