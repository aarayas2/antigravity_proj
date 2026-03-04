import pandas as pd
import pandas_ta
import numpy as np
import plotly.graph_objects as go

def apply_strategy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.ta.sma(length=20, append=True, col_names=("SMA_20",))
    df.ta.sma(length=50, append=True, col_names=("SMA_50",))
    
    df['Signal'] = 0.0
    df['Signal'] = np.where(df['SMA_20'] > df['SMA_50'], 1.0, 0.0)
    df['Position'] = df['Signal'].diff()
    return df

def needs_subplots() -> bool:
    return False

def add_traces(fig, df_with_signals, main_row, sub_row):
    if main_row:
        fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['SMA_20'], line=dict(color='orange', width=1.5), name='SMA 20'), row=main_row, col=1)
        fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['SMA_50'], line=dict(color='blue', width=1.5), name='SMA 50'), row=main_row, col=1)
    else:
        fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['SMA_20'], line=dict(color='orange', width=1.5), name='SMA 20'))
        fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['SMA_50'], line=dict(color='blue', width=1.5), name='SMA 50'))

def get_signals(df_with_signals: pd.DataFrame):
    buy_signals = df_with_signals[df_with_signals['Position'] == 1.0] if 'Position' in df_with_signals.columns else pd.DataFrame()
    sell_signals = df_with_signals[df_with_signals['Position'] == -1.0] if 'Position' in df_with_signals.columns else pd.DataFrame()
    return buy_signals, sell_signals
