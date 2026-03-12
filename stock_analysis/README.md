# Interactive Stock Strategy Analysis

This is a Dash-based web application that allows users to interactively analyze stock data and visualize the performance of various trading strategies over time.

## Architecture & Code Structure

The application has been refactored into a multi-page Dash structure for improved maintainability:
- **`app.py`**: The main entry point handling multi-page routing and the CLI batch mode.
- **`pages/strategy_chart.py`**: Contains the interactive Charting interface where users can select tickers and analyze specific strategies over time.
- **`pages/strategy_statistics.py`**: A dedicated page displaying a dynamically sortable and filterable table of previously computed strategy statistics.
- **`utils.py`**: A shared module housing common data loading, strategy application, and persistence logic.

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
- **Sortable Statistics:** Easily compare strategies across different tickers using the sortable native data table on the Strategy Statistics page.

## Installation & Setup

1. Ensure you have Python 3.9+ installed.
2. Clone or download this project.
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the Dash app:
   ```bash
   python stock_analysis/app.py
   ```
5. Open your web browser to the provided local URL (typically `http://localhost:8050`).

## Testing

To run the unit tests for this project, use `pytest` from the root directory:

```bash
python3 -m pytest stock_analysis/tests/
```

Individual tests can also be run specifically:

```bash
python3 -m pytest stock_analysis/tests/test_persistence.py
```

## How to use

### Web Interface
1. **Ticker Selection:** In the main top control panel on the Analysis page, type a valid symbol (e.g., `AAPL`, `MSFT`, `TSLA`) into the "Stock Ticker Symbol" field. You can press the **Enter** key or click the "Compute Analysis" button to execute. The application remembers up to your last 20 searched tickers.
2. **Strategy Selection:** Pick a strategy from the generated charts (SMA Crossover, Bollinger Bands, RSI, MACD).
3. **Date Range:** Adjust the slider to set the boundaries for the backtest. By default, it covers the last 1 year.
4. **Strategy Statistics:** Navigate to the "Stats Table" page to view a sortable history of all computed strategies. You can sort by Average Return, Strategy, and Win Rate.

### Batch Mode
You can run the analysis from the command line without starting the web server. This is useful for pre-calculating statistics for one or more tickers.

To run batch mode, provide the `--ticker` argument followed by a ticker or a semicolon-separated list of tickers:

```bash
# Run for a single ticker
python stock_analysis/app.py --ticker "MSFT"

# Run for multiple tickers (processed concurrently)
python stock_analysis/app.py --ticker "MSFT;AAPL;GOOGL"
```

The batch mode will automatically use the maximum available date range (e.g., last 5 years up to today) and will save the computed statistics to `data/stats.json` for later viewing in the web interface.
