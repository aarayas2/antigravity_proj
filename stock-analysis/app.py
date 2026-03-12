"""
Main entry point for the Stock Analysis App.
Supports both interactive Dash web UI and batch CLI analysis modes.
"""
import argparse
from collections import defaultdict
import os
import sys

import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc

# Ensure pages directory and current directory are in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import stats_manager, get_date_ranges  # pylint: disable=wrong-import-position,import-error

# Import layout and components after persistence is initialized
from pages.strategy_chart import layout as strategy_chart_layout  # pylint: disable=wrong-import-position,import-error
from pages.strategy_chart import run_analysis_for_ticker  # pylint: disable=wrong-import-position,import-error
from pages.strategy_statistics import layout as strategy_statistics_layout  # pylint: disable=wrong-import-position,import-error


# Dash App Initialization
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True
)
server = app.server

app.title = "Strategy Analysis"

def run_batch_mode(tickers_str: str):
    """
    Executes the batch analysis for a list of tickers sequentially.
    """
    # Deduplicate tickers while preserving order (to avoid redundant processing)
    tickers = list(dict.fromkeys(t.strip().upper() for t in tickers_str.split(";") if t.strip()))
    if not tickers:
        print("No valid tickers provided for batch mode.")
        return {}

    # Use max_date and min_date as defined for the full range (slider max/min)
    date_ranges = get_date_ranges()
    end_date_obj = date_ranges["max_date"]
    start_date_obj = date_ranges["min_date"]

    print(
        f"Starting batch analysis for {len(tickers)} ticker(s) "
        f"from {start_date_obj} to {end_date_obj}..."
    )

    success_count = 0
    strategy_groups = defaultdict(list)
    batch_stats = []

    # Pre-compute constant date strings to avoid redundant string formatting in the loop
    date_begin_str = start_date_obj.strftime('%Y-%m-%d')
    date_end_str = end_date_obj.strftime('%Y-%m-%d')

    for ticker in tickers:
        print(f"[{ticker}] Starting analysis...")
        result = run_analysis_for_ticker(ticker, start_date_obj, end_date_obj, is_batch_mode=True)
        if result is None:
            print(f"[{ticker}] Failed to load data.")
            continue

        # Collect stats for batch save
        batch_stats.append({
            'ticker': ticker,
            'date_begin': date_begin_str,
            'date_end': date_end_str,
            'strategies_metrics': result["metrics"]
        })

        print(f"[{ticker}] Analysis complete.")
        success_count += 1

        if result.get("buy_signals"):
            # ⚡ Performance Optimization:
            # Instead of accumulating dicts into an intermediate `buy_zone_signals` list and
            # iterating over it a second time, we directly populate `strategy_groups` here.
            for strategy in result["buy_signals"]:
                strategy_groups[strategy].append(ticker)
    # Save all stats in one batch operation
    if batch_stats:
        print(f"Saving statistics for {len(batch_stats)} ticker(s)...")
        stats_manager.save_stats_batch(batch_stats)

    print(
        f"Batch analysis finished. "
        f"Successfully processed {success_count}/{len(tickers)} ticker(s)."
    )

    return dict(strategy_groups)

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
    """Callback to render the appropriate page layout based on URL."""
    if pathname == '/stats':
        if callable(strategy_statistics_layout):
            return strategy_statistics_layout()
        return strategy_statistics_layout

    if callable(strategy_chart_layout):
        return strategy_chart_layout()
    return strategy_chart_layout

def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description="Stock Analysis App")
    parser.add_argument(
        "--ticker",
        type=str,
        help="Run in batch mode for provided ticker(s), separated by semicolons (e.g., 'MSFT;AAPL')"
    )
    args = parser.parse_args()

    if args.ticker:
        run_batch_mode(args.ticker)
    else:
        app.run(debug=False, port=8050)

if __name__ == '__main__':
    main()
