import pandas as pd
import plotly.graph_objects as go

def apply_strategy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        return df

    bbands = df.ta.bbands(length=20, std=2)
    if bbands is not None and not bbands.empty and 'BBL_20_2.0_2.0' in bbands.columns and 'BBU_20_2.0_2.0' in bbands.columns:
        df = pd.concat([df, bbands], axis=1)
        df['Signal'] = 0.0
        mask_buy = (df['Close'] < df['BBL_20_2.0_2.0']).fillna(False).to_numpy(dtype=bool)
        mask_sell = (df['Close'] > df['BBU_20_2.0_2.0']).fillna(False).to_numpy(dtype=bool)

        import numpy as np
        df['Signal'] = np.where(mask_buy, 1.0, df['Signal'])
        df['Signal'] = np.where(mask_sell, -1.0, df['Signal'])
        df['Position'] = df['Signal']
    return df

def needs_subplots() -> bool:
    return False

def add_traces(fig, df_with_signals, main_row, sub_row):
    if 'BBU_20_2.0_2.0' in df_with_signals.columns:
        if main_row:
            fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['BBU_20_2.0_2.0'], line=dict(color='gray', width=1, dash='dot'), name='Upper Band'), row=main_row, col=1)
            fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['BBL_20_2.0_2.0'], line=dict(color='gray', width=1, dash='dot'), name='Lower Band', fill='tonexty'), row=main_row, col=1)
            fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['BBM_20_2.0_2.0'], line=dict(color='blue', width=1.5), name='Middle Band'), row=main_row, col=1)
        else:
            fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['BBU_20_2.0_2.0'], line=dict(color='gray', width=1, dash='dot'), name='Upper Band'))
            fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['BBL_20_2.0_2.0'], line=dict(color='gray', width=1, dash='dot'), name='Lower Band', fill='tonexty'))
            fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['BBM_20_2.0_2.0'], line=dict(color='blue', width=1.5), name='Middle Band'))

def get_signals(df_with_signals: pd.DataFrame):
    buy_signals = df_with_signals[df_with_signals['Signal'] == 1.0] if 'Signal' in df_with_signals.columns else pd.DataFrame()
    sell_signals = df_with_signals[df_with_signals['Signal'] == -1.0] if 'Signal' in df_with_signals.columns else pd.DataFrame()
    return buy_signals, sell_signals
