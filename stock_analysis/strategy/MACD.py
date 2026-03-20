"""
MACD strategy implementation.
"""
# pylint: disable=invalid-name
import pandas as pd
import pandas_ta # pylint: disable=unused-import
import plotly.graph_objects as go

def apply_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """Applies the MACD strategy to the dataframe."""
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    if macd is not None and not macd.empty and 'MACD_12_26_9' in macd.columns:
        df = pd.concat([df, macd], axis=1)

        df['Signal'] = 0.0
        df.loc[df['MACD_12_26_9'] > df['MACDs_12_26_9'], 'Signal'] = 1.0
        df['Position'] = df['Signal'].diff()
        return df
    return df.copy()

def needs_subplots() -> bool:
    """Returns whether this strategy needs subplots."""
    return True

def add_traces(fig, df_with_signals, main_row, sub_row):
    """Adds MACD traces to the given figure."""
    # pylint: disable=unused-argument
    if 'MACD_12_26_9' in df_with_signals.columns:
        fig.add_trace(go.Scatter(
            x=df_with_signals.index, y=df_with_signals['MACD_12_26_9'],
            line={'color': 'blue', 'width': 1.5}, name='MACD Line'
        ), row=sub_row, col=1)
        fig.add_trace(go.Scatter(
            x=df_with_signals.index, y=df_with_signals['MACDs_12_26_9'],
            line={'color': 'orange', 'width': 1.5}, name='Signal Line'
        ), row=sub_row, col=1)
        colors = ['green' if val >= 0 else 'red'
                  for val in df_with_signals['MACDh_12_26_9']]
        fig.add_trace(go.Bar(
            x=df_with_signals.index, y=df_with_signals['MACDh_12_26_9'],
            marker_color=colors, name='MACD Hist'
        ), row=sub_row, col=1)

def get_signals(df_with_signals: pd.DataFrame):
    """Extracts buy and sell signals from the dataframe."""
    buy_signals = (df_with_signals[df_with_signals['Position'] == 1.0]
                   if 'Position' in df_with_signals.columns else pd.DataFrame())
    sell_signals = (df_with_signals[df_with_signals['Position'] == -1.0]
                    if 'Position' in df_with_signals.columns else pd.DataFrame())
    return buy_signals, sell_signals
