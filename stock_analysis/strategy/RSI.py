import pandas as pd
import plotly.graph_objects as go

def apply_strategy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.ta.rsi(length=14, append=True, col_names=("RSI_14",))
    
    df['Signal'] = 0.0
    df.loc[df['RSI_14'] < 30, 'Signal'] = 1.0
    df.loc[df['RSI_14'] > 70, 'Signal'] = -1.0
    df['Position'] = df['Signal']
    return df

def needs_subplots() -> bool:
    return True

def add_traces(fig, df_with_signals, main_row, sub_row):
    fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['RSI_14'], line=dict(color='purple', width=1.5), name='RSI 14'), row=sub_row, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=sub_row, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="green", row=sub_row, col=1)

def get_signals(df_with_signals: pd.DataFrame):
    buy_signals = df_with_signals[df_with_signals['Signal'] == 1.0] if 'Signal' in df_with_signals.columns else pd.DataFrame()
    sell_signals = df_with_signals[df_with_signals['Signal'] == -1.0] if 'Signal' in df_with_signals.columns else pd.DataFrame()
    return buy_signals, sell_signals
