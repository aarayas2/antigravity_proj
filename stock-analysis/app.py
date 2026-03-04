import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import argparse
import sys
import os

# Ensure pages directory and current directory are in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import stats_manager, max_date, min_date

# Import layout and components after persistence is initialized
from pages.strategy_chart import layout as strategy_chart_layout
from pages.strategy_chart import run_analysis_for_ticker
from pages.strategy_statistics import layout as strategy_statistics_layout

# Dash App Initialization
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
server = app.server

app.title = "Strategy Analysis"

def run_batch_mode(tickers_str: str):
    """
    Executes the batch analysis for a list of tickers sequentially.
    """
    tickers = [t.strip().upper() for t in tickers_str.split(";") if t.strip()]
    if not tickers:
        print("No valid tickers provided for batch mode.")
        return

    # Use max_date and min_date as defined for the full range (slider max/min)
    end_date_obj = max_date
    start_date_obj = min_date
    
    print(f"Starting batch analysis for {len(tickers)} ticker(s) from {start_date_obj} to {end_date_obj}...")
    
    success_count = 0
    buy_zone_signals = []
    
    for ticker in tickers:
        print(f"[{ticker}] Starting analysis...")
        result = run_analysis_for_ticker(ticker, start_date_obj, end_date_obj, is_batch_mode=True)
        if result is None:
            print(f"[{ticker}] Failed to load data.")
            continue
        
        # Save stats
        date_begin_str = start_date_obj.strftime('%Y-%m-%d')
        date_end_str = end_date_obj.strftime('%Y-%m-%d')
        stats_manager.save_stats(ticker, date_begin_str, date_end_str, result["metrics"])
        print(f"[{ticker}] Analysis complete and stats saved.")
        success_count += 1
        
        if result.get("buy_signals"):
            for strategy in result["buy_signals"]:
                buy_zone_signals.append({"Ticker": ticker, "Strategy": strategy})
        
    print(f"Batch analysis finished. Successfully processed {success_count}/{len(tickers)} ticker(s).")
    
    if buy_zone_signals:
        print("\n--- Buy Zone Signals ---")
        for signal in buy_zone_signals:
            print(f"Ticker: {signal['Ticker']}, Strategy: {signal['Strategy']}")

# --- Main App Layout ---
app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),

    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Analysis", href="/")),
            dbc.NavItem(dbc.NavLink("Stats Table", href="/stats")),
        ],
        brand="📈 Stock Strategy Analysis",
        brand_href="/",
        color="primary",
        dark=True,
        className="mb-4",
    ),

    html.Div(id='page-content')
], fluid=True, className="p-4")

@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/stats':
        return strategy_statistics_layout
    else:
        return strategy_chart_layout

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Stock Analysis App")
    parser.add_argument("--ticker", type=str, help="Run in batch mode for provided ticker(s), separated by semicolons (e.g., 'MSFT;AAPL')")
    args = parser.parse_args()

    if args.ticker:
        run_batch_mode(args.ticker)
    else:
        app.run(debug=False, port=8050)
