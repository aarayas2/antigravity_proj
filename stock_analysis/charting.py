"""
Charting Module
===============

This module provides functions for generating the Plotly Dash charts used
to visualize stock prices, technical indicators, and trade executions. 
It uses the Factory pattern (`TradeTooltipFactory`) for drawing complex 
trade window visualizations.
"""

from typing import Dict, Any, Tuple, Optional

import pandas as pd  # pylint: disable=import-error
import plotly.graph_objects as go  # pylint: disable=import-error
from plotly.subplots import make_subplots  # pylint: disable=import-error

from strategy import STRATEGIES  # pylint: disable=import-error
from trade_visuals import TradeTooltipFactory  # pylint: disable=import-error

class MockFig:
    """
    Dummy wrapper to maintain compatibility between go.Figure and
    make_subplots when adding traces to rows/cols.
    """
    def __init__(self, fig):
        self.fig = fig

    def add_trace(self, trace, row=None, col=None):  # pylint: disable=unused-argument
        """Add trace to figure."""
        self.fig.add_trace(trace)

    def update_layout(self, **kwargs):
        """Update figure layout."""
        self.fig.update_layout(**kwargs)

    def add_vrect(self, **kwargs):
        """Add vertical rectangle."""
        self.fig.add_vrect(**kwargs)

    def add_hline(self, **kwargs):
        """Add horizontal line."""
        self.fig.add_hline(**kwargs)

def _setup_figure(strategy: str) -> Tuple[go.Figure, Optional[int], Optional[int]]:
    """Initializes the figure, deciding whether subplots are needed."""
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
        main_row = None
        sub_row = None
    return fig, main_row, sub_row

def _add_trade_traces(
    fig: go.Figure,
    df_with_signals: pd.DataFrame,
    metrics: Dict[str, Any],
    main_row: Optional[int]
) -> None:
    """Draws trade duration windows with tooltips."""
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

def _add_candlestick_trace(
    fig: go.Figure,
    df_with_signals: pd.DataFrame,
    main_row: Optional[int]
) -> None:
    """Adds the main candlestick chart."""
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

def _add_strategy_traces(
    fig: go.Figure,
    df_with_signals: pd.DataFrame,
    strategy: str,
    main_row: Optional[int],
    sub_row: Optional[int]
) -> None:
    """Adds strategy-specific traces."""
    if strategy in STRATEGIES:
        STRATEGIES[strategy]["add_traces"](fig, df_with_signals, main_row, sub_row)

def _add_signal_traces(
    fig: go.Figure,
    df_with_signals: pd.DataFrame,
    strategy: str,
    main_row: Optional[int]
) -> None:
    """Plots Buy/Sell signals on the main chart."""
    buy_signals = pd.DataFrame()
    sell_signals = pd.DataFrame()
    if strategy in STRATEGIES:
        buy_signals, sell_signals = STRATEGIES[strategy]["get_signals"](df_with_signals)

    if not buy_signals.empty:
        trace = go.Scatter(
            x=buy_signals.index, y=buy_signals['Low'] * 0.98,
            mode='markers',
            marker={"symbol": 'triangle-up', "size": 12, "color": 'green'},
            name='Buy Signal'
        )
        if main_row:
            fig.add_trace(trace, row=main_row, col=1)
        else:
            fig.add_trace(trace)

    if not sell_signals.empty:
        trace = go.Scatter(
            x=sell_signals.index, y=sell_signals['High'] * 1.02,
            mode='markers',
            marker={"symbol": 'triangle-down', "size": 12, "color": 'red'},
            name='Sell Signal'
        )
        if main_row:
            fig.add_trace(trace, row=main_row, col=1)
        else:
            fig.add_trace(trace)

def _add_traces(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    fig: go.Figure,
    df_with_signals: pd.DataFrame,
    strategy: str,
    metrics: Dict[str, Any],
    main_row: Optional[int],
    sub_row: Optional[int]
) -> None:
    """Adds all traces (trades, candlesticks, strategy lines, signals) to the figure."""
    _add_trade_traces(fig, df_with_signals, metrics, main_row)
    _add_candlestick_trace(fig, df_with_signals, main_row)
    _add_strategy_traces(fig, df_with_signals, strategy, main_row, sub_row)
    _add_signal_traces(fig, df_with_signals, strategy, main_row)

def _update_layout(fig: go.Figure, main_row: Optional[int]) -> None:
    """Updates figure layout and axes visibility."""
    fig.update_layout(
        height=700, template="plotly_dark",
        margin={"l": 0, "r": 0, "t": 30, "b": 0}
    )

    rangeselector = {
        "buttons": [
            {"count": 1, "label": "1m", "step": "month", "stepmode": "backward"},
            {"count": 6, "label": "6m", "step": "month", "stepmode": "backward"},
            {"count": 1, "label": "1y", "step": "year", "stepmode": "backward"},
            {"step": "all"}
        ]
    }

    if main_row:
        fig.update_xaxes(rangeslider_visible=False, rangeselector=rangeselector, row=1, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=2, col=1)
    else:
        fig.update_xaxes(rangeslider_visible=False, rangeselector=rangeselector)

def create_strategy_chart(
    df_with_signals: pd.DataFrame,
    strategy: str,
    metrics: Dict[str, Any]
) -> go.Figure:
    """
    Generates a full Plotly Figure for a given strategy.

    Args:
        df_with_signals: The DataFrame containing price data and strategy signals.
        strategy: The name of the strategy to plot.
        metrics: The calculated metrics dictionary containing trades history.

    Returns:
        go.Figure: The fully configured Plotly chart.
    """
    fig, main_row, sub_row = _setup_figure(strategy)
    _add_traces(fig, df_with_signals, strategy, metrics, main_row, sub_row)
    _update_layout(fig, main_row)

    return fig
