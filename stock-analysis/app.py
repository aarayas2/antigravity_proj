import streamlit as st
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import load_data, apply_strategy, calculate_metrics

# Streamlit Page Config
st.set_page_config(page_title="Interactive Stock Analysis", layout="wide")
st.title("📈 Interactive Stock Strategy Analysis")

# Sidebar - User Inputs
st.sidebar.header("Configuration")
ticker = st.sidebar.text_input("Stock Ticker Symbol", value="AAPL").upper()
strategy = st.sidebar.selectbox("Trading Strategy", ["SMA Crossover", "Bollinger Bands", "RSI", "MACD"])

end_date_default = datetime.date.today()
start_date_default = end_date_default - datetime.timedelta(days=365)
start_date = st.sidebar.date_input("Start Date", start_date_default)
end_date = st.sidebar.date_input("End Date", end_date_default)

compute_btn = st.sidebar.button("Compute Analysis", use_container_width=True)

if compute_btn or "app_state" not in st.session_state:
    st.session_state["app_state"] = "loaded"
    
    with st.spinner(f"Fetching data for {ticker}..."):
        df = load_data(ticker, start_date, end_date)
        
        if df is None:
            st.error(f"Failed to load data for {ticker}. Please check the ticker symbol and try again.")
        else:
            with st.spinner("Applying strategy and calculating indicators..."):
                df_with_signals = apply_strategy(df, strategy)
                metrics = calculate_metrics(df_with_signals, strategy)
                
            # Layout: Top row for metrics
            st.subheader(f"Strategy Performance: {strategy} ({ticker})")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Total Return", value=metrics["Total Return"])
            with col2:
                st.metric(label="Number of Trades", value=metrics["Number of Trades"])
            with col3:
                st.metric(label="Win Rate", value=metrics["Win Rate"])
                
            st.markdown("---")
            
            # Visualization Section
            st.subheader("Price Chart & Indicators")
            
            # Create Plotly Figure with Subplots if needed
            if strategy in ["RSI", "MACD"]:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                    row_heights=[0.7, 0.3],
                                    vertical_spacing=0.08)
                main_row = 1
                sub_row = 2
            else:
                fig = go.Figure()
                # Dummy subplots interface compatibility
                class MockFig:
                    def __init__(self, fig): self.fig = fig
                    def add_trace(self, trace, row=None, col=None): self.fig.add_trace(trace)
                    def update_layout(self, **kwargs): self.fig.update_layout(**kwargs)
                fig_wrapper = MockFig(fig)
                fig = fig_wrapper.fig # Overwrite for simplicity in charting later
                main_row = None
                sub_row = None
            
            
            # Main Candlestick Chart
            candlestick = go.Candlestick(x=df_with_signals.index,
                                         open=df_with_signals['Open'],
                                         high=df_with_signals['High'],
                                         low=df_with_signals['Low'],
                                         close=df_with_signals['Close'],
                                         name="Price")
            if main_row:
                fig.add_trace(candlestick, row=main_row, col=1)
            else:
                fig.add_trace(candlestick)

            
            # Overlays based on Strategy
            if strategy == "SMA Crossover":
                 if main_row:
                     fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['SMA_20'], line=dict(color='orange', width=1.5), name='SMA 20'), row=main_row, col=1)
                     fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['SMA_50'], line=dict(color='blue', width=1.5), name='SMA 50'), row=main_row, col=1)
                 else:
                     fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['SMA_20'], line=dict(color='orange', width=1.5), name='SMA 20'))
                     fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['SMA_50'], line=dict(color='blue', width=1.5), name='SMA 50'))
            
            elif strategy == "Bollinger Bands":
                 if 'BBU_20_2.0_2.0' in df_with_signals.columns:
                     if main_row:
                         fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['BBU_20_2.0_2.0'], line=dict(color='gray', width=1, dash='dot'), name='Upper Band'), row=main_row, col=1)
                         fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['BBL_20_2.0_2.0'], line=dict(color='gray', width=1, dash='dot'), name='Lower Band', fill='tonexty'), row=main_row, col=1)
                         fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['BBM_20_2.0_2.0'], line=dict(color='blue', width=1.5), name='Middle Band'), row=main_row, col=1)
                     else:
                         fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['BBU_20_2.0_2.0'], line=dict(color='gray', width=1, dash='dot'), name='Upper Band'))
                         fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['BBL_20_2.0_2.0'], line=dict(color='gray', width=1, dash='dot'), name='Lower Band', fill='tonexty'))
                         fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['BBM_20_2.0_2.0'], line=dict(color='blue', width=1.5), name='Middle Band'))


            # Subplot Indicators
            elif strategy == "RSI":
                 fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['RSI_14'], line=dict(color='purple', width=1.5), name='RSI 14'), row=sub_row, col=1)
                 # Add overbought/oversold levels
                 fig.add_hline(y=70, line_dash="dot", line_color="red", row=sub_row, col=1)
                 fig.add_hline(y=30, line_dash="dot", line_color="green", row=sub_row, col=1)
            
            elif strategy == "MACD":
                 if 'MACD_12_26_9' in df_with_signals.columns:
                     fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['MACD_12_26_9'], line=dict(color='blue', width=1.5), name='MACD Line'), row=sub_row, col=1)
                     fig.add_trace(go.Scatter(x=df_with_signals.index, y=df_with_signals['MACDs_12_26_9'], line=dict(color='orange', width=1.5), name='Signal Line'), row=sub_row, col=1)
                     # Histogram
                     colors = ['green' if val >= 0 else 'red' for val in df_with_signals['MACDh_12_26_9']]
                     fig.add_trace(go.Bar(x=df_with_signals.index, y=df_with_signals['MACDh_12_26_9'], marker_color=colors, name='MACD Hist'), row=sub_row, col=1)


            # Plot Buy/Sell signals on main chart
            buy_signals = df_with_signals[df_with_signals['Signal'] == 1.0] if 'Signal' in df_with_signals.columns else pd.DataFrame()
            sell_signals = df_with_signals[df_with_signals['Signal'] == -1.0] if 'Signal' in df_with_signals.columns else pd.DataFrame()
            
            # Use 'Position' diff for crossover entries instead of raw Signals to avoid plotting on every bar
            if strategy in ["SMA Crossover", "MACD"]:
                 buy_signals = df_with_signals[df_with_signals['Position'] == 1.0]
                 sell_signals = df_with_signals[df_with_signals['Position'] == -1.0]
            
            if not buy_signals.empty:
                trace = go.Scatter(x=buy_signals.index, y=buy_signals['Low'] * 0.98,
                                   mode='markers', marker=dict(symbol='triangle-up', size=12, color='green'),
                                   name='Buy Signal')
                if main_row: fig.add_trace(trace, row=main_row, col=1)
                else: fig.add_trace(trace)
                
            if not sell_signals.empty:
                trace = go.Scatter(x=sell_signals.index, y=sell_signals['High'] * 1.02,
                                   mode='markers', marker=dict(symbol='triangle-down', size=12, color='red'),
                                   name='Sell Signal')
                if main_row: fig.add_trace(trace, row=main_row, col=1)
                else: fig.add_trace(trace)


            # Layout updates
            fig.update_layout(height=700, template="plotly_dark" if st.session_state.get('theme') == 'dark' else "plotly_white",
                              xaxis_rangeslider_visible=False,
                              margin=dict(l=0, r=0, t=30, b=0))
            if main_row:
                 fig.update_xaxes(rangeslider_visible=False) # Ensure rangeslider off for all subplots

            st.plotly_chart(fig, use_container_width=True)
