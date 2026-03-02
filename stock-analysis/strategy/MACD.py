import pandas as pd
import numpy as np
import plotly.graph_objects as go

def apply_strategy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    if macd is not None:
         df = pd.concat([df, macd], axis=1)
         
         df['Signal'] = 0.0
         df['Signal'] = np.where(df['MACD_12_26_9'] > df['MACDs_12_26_9'], 1.0, 0.0)
         df['Position'] = df['Signal'].diff()
    return df

def needs_subplots() -> bool:
    return True

def add_traces(fig, df_with_signals, main_row, sub_row):
    if 'MACD_12_26_9' in df_with_signals.columns:
         fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['MACD_12_26_9'], line=dict(color='blue', width=1.5), name='MACD Line'), row=sub_row, col=1)
         fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['MACDs_12_26_9'], line=dict(color='orange', width=1.5), name='Signal Line'), row=sub_row, col=1)
         colors = ['green' if val >= 0 else 'red' for val in df_with_signals['MACDh_12_26_9']]
         fig.add_trace(go.Bar(x=df_with_signals.index, y=df_with_signals['MACDh_12_26_9'], marker_color=colors, name='MACD Hist'), row=sub_row, col=1)

def get_signals(df_with_signals: pd.DataFrame):
    buy_signals = df_with_signals[df_with_signals['Position'] == 1.0] if 'Position' in df_with_signals.columns else pd.DataFrame()
    sell_signals = df_with_signals[df_with_signals['Position'] == -1.0] if 'Position' in df_with_signals.columns else pd.DataFrame()
    return buy_signals, sell_signals
