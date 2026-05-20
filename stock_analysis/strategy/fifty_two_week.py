"""
52-Week Range Strategy implementation.
Returns a buy signal when the price is within 15% of the 52-week low
AND within 10% of the 52-week high.
"""
import pandas as pd
import plotly.graph_objects as go

def apply_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """Applies the 52-Week Range strategy to the DataFrame."""
    df = df.copy()
    if df.empty or 'High' not in df.columns or 'Low' not in df.columns or 'Close' not in df.columns:
        return df

    # Calculate 52-week high and low (assuming ~252 trading days in a year)
    df['52W_High'] = df['High'].rolling(window=252, min_periods=1).max()
    df['52W_Low'] = df['Low'].rolling(window=252, min_periods=1).min()

    df['Signal'] = 0.0

    # Conditions:
    # 1. Price is within 15% of the 52-week low: Close <= 52W_Low * 1.15
    # 2. Price is within 10% of the 52-week high: Close >= 52W_High * 0.90
    cond1 = df['Close'] <= df['52W_Low'] * 1.15
    cond2 = df['Close'] >= df['52W_High'] * 0.90

    df.loc[cond1 & cond2, 'Signal'] = 1.0

    # Since it's just checking conditions, we use Signal as Position directly
    # or calculate Position based on Signal diff?
    df['Position'] = df['Signal']
    return df

def needs_subplots() -> bool:
    """Returns False as 52-Week Range does not need subplots."""
    return False

def add_traces(fig, df_with_signals, main_row, sub_row):  # pylint: disable=unused-argument
    """Adds 52-Week High/Low traces to the figure."""
    if '52W_High' in df_with_signals.columns and '52W_Low' in df_with_signals.columns:
        if main_row:
            fig.add_trace(go.Scatter(
                x=df_with_signals.index,
                y=df_with_signals['52W_High'],
                line={'color': 'green', 'width': 1, 'dash': 'dash'},
                name='52W High'
            ), row=main_row, col=1)
            fig.add_trace(go.Scatter(
                x=df_with_signals.index,
                y=df_with_signals['52W_Low'],
                line={'color': 'red', 'width': 1, 'dash': 'dash'},
                name='52W Low'
            ), row=main_row, col=1)
        else:
            fig.add_trace(go.Scatter(
                x=df_with_signals.index,
                y=df_with_signals['52W_High'],
                line={'color': 'green', 'width': 1, 'dash': 'dash'},
                name='52W High'
            ))
            fig.add_trace(go.Scatter(
                x=df_with_signals.index,
                y=df_with_signals['52W_Low'],
                line={'color': 'red', 'width': 1, 'dash': 'dash'},
                name='52W Low'
            ))

def get_signals(df_with_signals: pd.DataFrame):
    """Returns buy and sell signals based on Position."""
    if 'Position' in df_with_signals.columns:
        # Based on how we define it, 1.0 is a buy signal
        buy_signals = df_with_signals[df_with_signals['Position'] == 1.0]
        # We don't define sell signals explicitly, but let's return empty DF for consistency
        sell_signals = df_with_signals[df_with_signals['Position'] == -1.0]
    else:
        buy_signals = pd.DataFrame()
        sell_signals = pd.DataFrame()
    return buy_signals, sell_signals

def run(ticker: str, start_date_obj, end_date_obj) -> bool:
    """Runs the 52-Week Range strategy for a ticker and returns True if it's in the buy zone."""
    from utils import load_data
    df = load_data(ticker, start_date_obj, end_date_obj)
    if df is None or df.empty:
        return False
    df = apply_strategy(df)
    if df.empty or 'Signal' not in df.columns:
        return False
    return df.iloc[-1]['Signal'] == 1.0
