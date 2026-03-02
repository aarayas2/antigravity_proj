# Interactive Stock Strategy Analysis

This is a Streamlit-based web application that allows users to interactively analyze stock data and visualize the performance of various trading strategies over time.

## Features

- **Dynamic Data fetching:** Analyzes any valid US stock ticker using real-time historical data from Yahoo Finance (`yfinance`).
- **Trading Strategies:**
  - Simple Moving Average (SMA) Crossover
  - Bollinger Bands Reversion
  - Relative Strength Index (RSI)
  - Moving Average Convergence Divergence (MACD)
- **Interactive Visualizations:** Renders beautiful, zoomable Candlestick charts using Plotly, complete with overlay indicators, sub-panels for oscillators, and visual markings for Buy/Sell signals.
- **Trade Duration Windows:** The chart plots transparent green and red windows to visualize exactly when you were continuously holding a long position, and whether it was profitable.
- **Performance Metrics:** Automatically calculates Total Return, Win Rate, and the overall Number of Trades for the selected strategy within your Date Range.

## Installation & Setup

1. Ensure you have Python 3.9+ installed.
2. Clone or download this project.
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```
5. Open your web browser to the provided local URL (typically `http://localhost:8501`).

## How to use
1. **Ticker Selection:** In the main top control panel, type a valid symbol (e.g., `AAPL`, `MSFT`, `TSLA`) into the "Stock Ticker Symbol" field. The application remembers up to your last 20 searched tickers.
2. **Strategy Selection:** Pick a strategy from the dropdown (SMA Crossover, Bollinger Bands, RSI, MACD).
3. **Date Range:** Adjust the slider to set the boundaries for the backtest. By default, it covers the last 1 year.
4. **Compute:** Click the "Compute Analysis" button. The app will fetch the data, process the strategy signals, and display the performance metrics alongside the interactive chart.
