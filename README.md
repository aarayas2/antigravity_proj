# Multi-Tool Application Suite

This repository contains two primary applications:
1. **Interactive Stock Strategy Analysis** (`stock_analysis/`)
2. **Wi-Fi QR Code Generator** (`wifi-qr/`)

---

## 1. Interactive Stock Strategy Analysis

This is a Dash-based web application that allows users to interactively analyze stock data and visualize the performance of various trading strategies over time.

### Features
- **Dynamic Data Fetching:** Analyzes any valid US stock ticker using real-time historical data from Yahoo Finance (`yfinance`).
- **Trading Strategies:**
  - Simple Moving Average (SMA) Crossover
  - Bollinger Bands Reversion
  - Relative Strength Index (RSI)
  - Moving Average Convergence Divergence (MACD)
- **Interactive Visualizations:** Renders beautiful, zoomable Candlestick charts using Plotly, complete with overlay indicators, sub-panels for oscillators, and visual markings for Buy/Sell signals.
- **Performance Metrics & Statistics:** Calculates Total Return, Win Rate, and Number of Trades. View sortable and filterable statistics comparing strategies across different tickers.

### Installation & Setup
From the root directory:

1. Install dependencies:
   ```bash
   pip install -r stock_analysis/requirements.txt
   ```
2. Run the application:
   ```bash
   python stock_analysis/app.py
   ```
3. Access the web interface at `http://localhost:8050`.

*Note: For batch mode processing, you can run `python stock_analysis/app.py --ticker "AAPL;MSFT"`.*

---

## 2. Wi-Fi QR Code Generator

This is a Streamlit web application that generates high-quality Wi-Fi QR codes. It allows users to input their Wi-Fi credentials and instantly creates a QR code that guests can scan to connect to the network without manually typing passwords.

### Features
- **Secure QR Generation:** Generates QR codes for WPA/WPA2/WPA3, WEP, or open networks. Supports hidden networks.
- **Customization:** Easily customize the QR code color, background color, size (scale), and border (quiet zone).
- **Beautiful UI:** Features a premium modern dark UI built with custom CSS.
- **Export Options:** Download the generated QR code as a PNG or SVG (vector) image.

### Installation & Setup
From the root directory:

1. Install dependencies:
   ```bash
   pip install -r wifi-qr/requirements.txt
   ```
2. Run the application:
   ```bash
   streamlit run wifi-qr/app.py
   ```
3. Open your web browser to the provided local URL (typically `http://localhost:8501`).
