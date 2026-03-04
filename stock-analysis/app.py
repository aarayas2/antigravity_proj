import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import datetime
import os
import argparse
import concurrent.futures
from utils import load_data, apply_strategy, calculate_metrics
from strategy import STRATEGIES
from charting import create_strategy_chart
from persistence import StatsManager, JsonStatsStorage

# Initialize Persistence Layer
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
stats_manager = StatsManager(JsonStatsStorage(STATS_FILE))

import dash_bootstrap_components as dbc
import pandas as pd

def run_analysis_for_ticker(ticker: str, start_date_obj: datetime.date, end_date_obj: datetime.date, is_batch_mode: bool = False):
    """
    Executes core analysis logic for a single ticker.
    Returns a dictionary of metrics if successful, or None if data could not be loaded.
    In batch mode, it bypasses generating Plotly figures and HTML components.
    """
    df = load_data(ticker, start_date_obj, end_date_obj)

    if df is None or df.empty:
        return None
        
    strategies_metrics = {}
    output_sections = []
    
    def process_strategy(strategy):
        df_with_signals = apply_strategy(df.copy(), strategy)
        metrics = calculate_metrics(df_with_signals, strategy)

        strategy_metric = {
            "Total Return": metrics["Total Return"],
            "Average Return": metrics["Average Return"],
            "Number of Trades": metrics["Number of Trades"],
            "Win Rate": metrics["Win Rate"]
        }
        
        section = None
        if not is_batch_mode:
            # Metrics Section
            metrics_row = dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H5("Total Return", className="card-title"),
                    html.H3(metrics["Total Return"], className="text-success" if float(metrics["Total Return"].strip('%')) >= 0 else "text-danger")
                ])), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H5("Average Return", className="card-title"),
                    html.H3(metrics["Average Return"], className="text-success" if float(metrics["Average Return"].strip('%')) >= 0 else "text-danger")
                ])), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H5("Number of Trades", className="card-title"),
                    html.H3(metrics["Number of Trades"], className="text-info")
                ])), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H5("Win Rate", className="card-title"),
                    html.H3(metrics["Win Rate"], className="text-warning")
                ])), md=3),
            ], className="mb-4")

            # Generate the Plotly figure
            fig = create_strategy_chart(df_with_signals, strategy, metrics)
            chart_section = dcc.Graph(figure=fig)

            section = html.Div([
                html.H3(f"Strategy Performance: {strategy} ({ticker})", className="mb-3"),
                metrics_row,
                html.Hr(),
                html.H3("Price Chart & Indicators", className="mb-3"),
                chart_section,
                html.Hr(style={'margin-top': '40px', 'margin-bottom': '40px', 'border-top': '2px solid white'})
            ])
            
        return strategy, strategy_metric, section

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_strategy, STRATEGIES.keys()))
        
    for strategy, strategy_metric, section in results:
        strategies_metrics[strategy] = strategy_metric
        if section is not None:
            output_sections.append(section)

    return {"metrics": strategies_metrics, "sections": output_sections}

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
        
    print(f"Batch analysis finished. Successfully processed {success_count}/{len(tickers)} ticker(s).")

# Dash App Initialization
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
server = app.server

app.title = "Interactive Stock Analysis"

# Default dates
max_date = datetime.date.today()
min_date = max_date - datetime.timedelta(days=365 * 5)
default_start = max_date - datetime.timedelta(days=365)

# Convert dates to ordinal for slider
min_date_ord = min_date.toordinal()
max_date_ord = max_date.toordinal()
default_start_ord = default_start.toordinal()
step_ord = 180 # ~6 months interval

# --- Page 2 Layout ---
page2_layout = html.Div([
    html.H2("Strategy Statistics", className="mb-4"),
    dbc.Row([
        dbc.Col([
            dbc.Label("Minimum Win Rate Filter (%)"),
            dcc.Slider(
                id='win-rate-slider',
                min=0,
                max=100,
                step=5,
                value=50,
                marks={i: f'{i}%' for i in range(0, 101, 10)}
            )
        ], md=6)
    ], className="mb-4"),
    html.Div(id='stats-table-container')
])

# --- Page 1 Layout ---
page1_layout = html.Div([
    dcc.Store(id='mru-store', storage_type='local', data=[]),
    html.Datalist(id='mru-tickers'),
    
    dbc.Row([
        dbc.Col([
            dbc.Label("Stock Ticker Symbol"),
            dbc.Input(
                id="ticker-input", 
                type="text", 
                value="AAPL", 
                style={'textTransform': 'uppercase'},
                list="mru-tickers",
                autocomplete="off"
            )
        ], md=4),
        
        dbc.Col([
            dbc.Label(id="date-range-label", children="Date Range"),
            html.Div([
                dcc.RangeSlider(
                    id='date-range-slider',
                    min=min_date_ord,
                    max=max_date_ord,
                    step=step_ord,
                    value=[default_start_ord, max_date_ord],
                    marks={
                        min_date_ord: min_date.strftime('%Y-%m-%d'),
                        max_date_ord: max_date.strftime('%Y-%m-%d')
                    },
                    updatemode='drag'
                )
            ], style={'padding-top': '10px'})
        ], md=6),
        
        dbc.Col([
            dbc.Label("\u00A0"), # Non-breaking space for alignment
            dbc.Button("Compute Analysis", id="compute-btn", color="primary", className="w-100", n_clicks=0)
        ], md=2)
    ], className="mb-4 align-items-end"),

    dbc.Spinner(
        html.Div(id="output-container")
    )
])

# --- Main App Layout ---
app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),

    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Analysis", href="/")),
            dbc.NavItem(dbc.NavLink("Stats Table", href="/stats")),
        ],
        brand="📈 Interactive Stock Strategy Analysis",
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
        return page2_layout
    else:
        return page1_layout

@callback(
    Output("date-range-label", "children"),
    Input("date-range-slider", "value")
)
def update_date_label(value):
    start_date = datetime.date.fromordinal(value[0])
    end_date = datetime.date.fromordinal(value[1])
    return f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

@callback(
    Output("mru-tickers", "children"),
    Input("mru-store", "data")
)
def update_datalist(mru_data):
    if not mru_data:
        return []
    return [html.Option(value=ticker) for ticker in mru_data]

@callback(
    Output("output-container", "children"),
    Output("mru-store", "data"),
    Input("compute-btn", "n_clicks"),
    State("ticker-input", "value"),
    State("date-range-slider", "value"),
    State("mru-store", "data")
)
def update_analysis(n_clicks, ticker, date_range, mru_data):
    if not ticker or not date_range:
        return html.Div("Please provide ticker and date range."), dash.no_update

    ticker = ticker.upper()
    start_date_obj = datetime.date.fromordinal(date_range[0])
    end_date_obj = datetime.date.fromordinal(date_range[1])

    result = run_analysis_for_ticker(ticker, start_date_obj, end_date_obj, is_batch_mode=False)

    if result is None:
        return dbc.Alert(f"Failed to load data for {ticker}. Please check the ticker symbol and try again.", color="danger"), dash.no_update
    
    # Update MRU data
    if mru_data is None:
        mru_data = []
    
    if ticker in mru_data:
        mru_data.remove(ticker)
    mru_data.insert(0, ticker)
    
    # Keep only the last 20 searched tickers
    mru_data = mru_data[:20]

    output_sections = result["sections"]
    strategies_metrics = result["metrics"]

    # Trigger save logic if on Maximum date range
    if date_range[0] == min_date_ord and date_range[1] == max_date_ord:
        date_begin_str = start_date_obj.strftime('%Y-%m-%d')
        date_end_str = end_date_obj.strftime('%Y-%m-%d')
        stats_manager.save_stats(ticker, date_begin_str, date_end_str, strategies_metrics)

    return html.Div(output_sections), mru_data

@callback(
    Output('stats-table-container', 'children'),
    Input('win-rate-slider', 'value')
)
def update_stats_table(min_win_rate):
    data = stats_manager._storage.read()

    rows = []
    for entry in data:
        for ticker, stats in entry.items():
            date_begin = stats.get('date-begin', 'N/A')
            date_end = stats.get('date-end', 'N/A')

            for strategy, metrics in stats.items():
                if strategy in ['date-begin', 'date-end']:
                    continue

                win_rate_str = metrics.get('Win Rate', '0%')
                try:
                    win_rate_val = float(win_rate_str.strip('%'))
                except ValueError:
                    win_rate_val = 0.0

                if win_rate_val > min_win_rate:
                    rows.append({
                        "Ticker": ticker,
                        "Date Begin": date_begin,
                        "Date End": date_end,
                        "Strategy": strategy,
                        "Total Return": metrics.get('Total Return', 'N/A'),
                        "Average Return": metrics.get('Average Return', 'N/A'),
                        "Number of Trades": metrics.get('Number of Trades', 'N/A'),
                        "Win Rate": win_rate_str
                    })

    if not rows:
        return dbc.Alert("No data available or no strategies meet the filter criteria.", color="info")

    df = pd.DataFrame(rows)

    table = dbc.Table.from_dataframe(
        df, striped=True, bordered=True, hover=True, color="dark", responsive=True
    )

    return table


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Interactive Stock Analysis App")
    parser.add_argument("--ticker", type=str, help="Run in batch mode for provided ticker(s), separated by semicolons (e.g., 'MSFT;AAPL')")
    args = parser.parse_args()

    if args.ticker:
        run_batch_mode(args.ticker)
    else:
        app.run(debug=False, port=8050)
