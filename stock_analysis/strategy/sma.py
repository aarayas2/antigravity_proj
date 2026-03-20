"""
Simple Moving Average (SMA) Strategy implementation.
"""
import pandas as pd
import pandas_ta  # pylint: disable=unused-import # Required to register .ta accessor
import plotly.graph_objects as go

def apply_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """Applies the SMA strategy to the DataFrame."""
    df = df.copy()
    df.ta.sma(length=20, append=True, col_names=("SMA_20",))
    df.ta.sma(length=50, append=True, col_names=("SMA_50",))

    df['Signal'] = 0.0
    if 'SMA_20' in df.columns and 'SMA_50' in df.columns:
        df.loc[df['SMA_20'] > df['SMA_50'], 'Signal'] = 1.0
    df['Position'] = df['Signal'].diff()
    return df

def needs_subplots() -> bool:
    """Returns False as SMA does not need subplots."""
    return False

def add_traces(fig, df_with_signals, main_row, sub_row):  # pylint: disable=unused-argument
    """Adds SMA traces to the figure."""
    if main_row:
        fig.add_trace(go.Scatter(
            x=df_with_signals.index,
            y=df_with_signals['SMA_20'],
            line={'color': 'orange', 'width': 1.5},
            name='SMA 20'
        ), row=main_row, col=1)
        fig.add_trace(go.Scatter(
            x=df_with_signals.index,
            y=df_with_signals['SMA_50'],
            line={'color': 'blue', 'width': 1.5},
            name='SMA 50'
        ), row=main_row, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=df_with_signals.index,
            y=df_with_signals['SMA_20'],
            line={'color': 'orange', 'width': 1.5},
            name='SMA 20'
        ))
        fig.add_trace(go.Scatter(
            x=df_with_signals.index,
            y=df_with_signals['SMA_50'],
            line={'color': 'blue', 'width': 1.5},
            name='SMA 50'
        ))

def get_signals(df_with_signals: pd.DataFrame):
    """Returns buy and sell signals based on Position."""
    if 'Position' in df_with_signals.columns:
        buy_signals = df_with_signals[df_with_signals['Position'] == 1.0]
        sell_signals = df_with_signals[df_with_signals['Position'] == -1.0]
    else:
        buy_signals = pd.DataFrame()
        sell_signals = pd.DataFrame()
    return buy_signals, sell_signals
